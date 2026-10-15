"""Árbol de etapas del expediente para el front (Gestionar y Consulta).

Contrato (lo usa ``routes/expediente_query.py`` en la clave ``etapas`` de
``GET /expedientes/{id}``; también ``GET /etapas/{id}``):

    async def leer_etapas(db, expediente, usuario) -> dict

Cada etapa / sub-proceso es un **nodo** con la misma forma (ver API.md §C.2):
``codigo, etiqueta, etapa_tipo, id, version, existe, habilitada,
motivos_bloqueo, encargado, tecnico, datos, proceso, acto, anexos,
acciones_disponibles`` + sus sub-nodos con nombre. Las reglas salen de
``services/validaciones.py`` (una sola definición); el front no recalcula nada.

Sin N+1: ``cargar_estado`` (consultas fijas) + procesos, revisiones,
anexos, comunicaciones y notificaciones en lote + una llamada a app-users
(nombres) y una a app-involved (terceros).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import Usuario
from core.permission import Permission
from db.models import Comunicacion, DocumentoAnexo, Expediente, Notificacion, TipoVinculo
from satc_shared.review_process import PENDIENTE_CARGA, RECHAZADO
from services.actos import (
    acciones_comunicacion_notificacion,
    se_notifica,
    serializar_comunicacion,
    serializar_notificacion,
)
from services.etapas import ETIQUETAS_CONCEPTO, ETIQUETAS_REQUERIMIENTO, Estado, cargar_estado
from services.expediente_involucrados import serializar_vinculos
from services.revision_documentos import (
    APROBADO_FIRMA,
    PERMISOS_REVISOR,
    permisos_de_usuario,
    procesos_vigentes,
    resumenes_procesos,
)
import services.users as users_svc
from services import validaciones as V

# Orden del plan §4 para ``etapa_actual`` (la etapa MÁS AVANZADA que existe).
ORDEN_ETAPAS: dict[str, int] = {
    "admite": 1, "concepto": 2, "requerimiento": 3, "decision": 4, "memorias": 5, "obras": 6,
}
ETIQUETAS_ETAPA: dict[str, str] = {
    "admite": "Etapa 1 · Auto que admite",
    "concepto": "Etapa 2 · Concepto técnico",
    "requerimiento": "Etapa 3 · Requerimiento",
    "decision": "Etapa 4 · Decisión",
    "memorias": "Etapa 5 · Memorias de cálculo",
    "obras": "Etapa 6 · Recibo a satisfacción de obras",
}

ETAPAS_CON_PROCESO = (
    "acto_admite", "concepto_tecnico", "requerimiento", "decision", "recurso_reposicion",
    "memorias_calculo", "recibo_satisfaccion_obras", "expediente_involucrado",
)


def _iso(v) -> Optional[str]:
    return v.isoformat() if v is not None else None


def _valor(v):
    return v.value if hasattr(v, "value") else v


class _Lector:
    def __init__(self, e: Estado, usuario: Usuario, permisos: frozenset[str]):
        self.e = e
        self.u = usuario
        self.gestor = usuario.super_gestion or Permission.MANAGE in permisos
        self.procesos: dict = {}
        self.resumenes: dict = {}
        self.anexos: dict[tuple[str, int], list] = {}
        self.comunicaciones: dict[int, Comunicacion] = {}
        self.notificaciones: dict[int, list[Notificacion]] = {}
        self.nombres: dict[int, Optional[str]] = {}
        self.notificables: set[int] = {v.involucrado_id for v in e.vinculos}

    # ─────────────────────────────────────────────────────── auxiliares
    def persona(self, user_id: Optional[int]) -> Optional[dict]:
        if not user_id:
            return None
        return {"id": user_id, "nombre": self.nombres.get(user_id)}

    def es_yo(self, user_id: Optional[int]) -> bool:
        return user_id is not None and user_id == self.u.user_id

    def proceso_de(self, etapa_tipo: str, ref_id: Optional[int]):
        return self.procesos.get((etapa_tipo, ref_id)) if ref_id else None

    def acto(self, acto_id: Optional[int], etapa_tipo: str, etapa_id: int, encargado_id: Optional[int]) -> Optional[dict]:
        """Misma forma que ``services.actos.serializar_acto`` + ``acciones_disponibles``
        (equivalente en lote de ``acciones_acto``)."""
        acto = self.e.acto(acto_id)
        if acto is None:
            return None
        com = self.comunicaciones.get(acto.id)
        notifs = self.notificaciones.get(acto.id, [])
        exitosas = sum(1 for n in notifs if n.notificacion_exitosa)
        data = {
            "id": acto.id,
            "tipo_acto": _valor(acto.tipo_acto),
            "clase_acto": acto.clase_acto,
            "numerado": acto.numerado,
            "fecha_numerado": _iso(acto.fecha_numerado),
            "documento_acto_administrativo_id": acto.documento_acto_administrativo_id,
            "documento_acto_id": acto.documento_acto_administrativo_id,
            "fecha_creacion": _iso(acto.fecha_creacion),
            "etapa_tipo": etapa_tipo,
            "etapa_id": etapa_id,
            "comunicacion": serializar_comunicacion(com),
            "notificacion": {
                "id": acto.id,
                "fecha_creacion": _iso(acto.fecha_creacion),
                "involucrados": [serializar_notificacion(n) for n in notifs],
            },
            # Regla provisional de B (TODO(negocio)): ≥1 notificación y todas exitosas.
            "notificado": bool(notifs) and exitosas == len(notifs),
        }
        acciones: list[str] = []
        if self.u.super_gestion or self.es_yo(encargado_id):
            acciones.append("editar_acto")
            if self.u.super_gestion:
                acciones.append("eliminar_acto")
            notificados = {n.involucrado_id for n in notifs}
            notificables = self.notificables if se_notifica(acto.tipo_acto) else set()
            acciones += acciones_comunicacion_notificacion(acto.tipo_acto, com is not None, notificados, notificables)
        data["acciones_disponibles"] = acciones
        return data

    def base(self, codigo: str, etiqueta: str, etapa_tipo: str, fila, *, existe: Optional[bool] = None) -> dict:
        existe = (fila is not None) if existe is None else existe
        return {
            "codigo": codigo,
            "etiqueta": etiqueta,
            "etapa_tipo": etapa_tipo,
            "id": fila.id if fila is not None else None,
            "version": getattr(fila, "version", None) if fila is not None else None,
            "existe": existe,
            "habilitada": existe,
            "motivos_bloqueo": [],
            "encargado": None,
            "tecnico": None,
            "datos": {},
            "proceso": None,
            "acto": None,
            "anexos": [],
            "acciones_disponibles": [],
        }

    def bloquear(self, n: dict, motivo: Optional[str]) -> None:
        if n["existe"]:
            return
        n["habilitada"] = motivo is None
        if motivo:
            n["motivos_bloqueo"].append(motivo)

    def con_proceso(self, n: dict, etapa_tipo: str, ref_id: Optional[int], encargado_id: Optional[int],
                    final_cargado: bool) -> None:
        p = self.proceso_de(etapa_tipo, ref_id)
        if p is None:
            return
        n["proceso"] = self.resumenes.get(p.id)
        acc = n["acciones_disponibles"]
        if self.es_yo(encargado_id) and p.activo:
            if p.estado in (PENDIENTE_CARGA, RECHAZADO):
                acc.append("subir_version")
            elif p.estado == APROBADO_FIRMA and not final_cargado:
                acc.append("cargar_version_final")
        if n["proceso"] and n["proceso"].get("puedo_revisar"):
            acc.append("revisar")

    def con_anexos(self, n: dict, etapa_tipo: str, fila) -> None:
        if fila is None:
            return
        n["anexos"] = self.anexos.get((etapa_tipo, fila.id), [])
        if self.gestor:
            n["acciones_disponibles"].append("gestionar_anexos")

    def cerrar(self, n: dict) -> dict:
        if self.u.super_gestion:
            n["acciones_disponibles"].append("super_cargar")
        return n

    # ──────────────────────────────────────────────────────── tipos de nodo
    def nodo_acto(
        self, codigo: str, etiqueta: str, etapa_tipo: str, fila, encargado_id: Optional[int], motivo: Optional[str], *,
        codigo_crear: str = "asignarme", existe: Optional[bool] = None, datos: Optional[dict] = None,
        anexos: bool = True, asignable: bool = True,
    ) -> dict:
        """Etapa con acto administrativo (abogado encargado, V2).

        ``asignable=False``: la fila existe sin encargado pero su "Asignarme"
        solo crea filas nuevas (acto_admite, requerimiento, decisión cargados
        por super gestión sin encargado): nadie se asigna, solo super gestión
        gestiona."""
        n = self.base(codigo, etiqueta, etapa_tipo, fila, existe=existe)
        n["datos"] = datos or {}
        n["encargado"] = self.persona(encargado_id)
        self.bloquear(n, motivo)
        if encargado_id is None and motivo is None and self.gestor and asignable:
            n["acciones_disponibles"].append(codigo_crear)
        if fila is not None:
            n["acto"] = self.acto(fila.acto_admin_id, etapa_tipo, fila.id, encargado_id)
            self.con_proceso(n, etapa_tipo, fila.id, encargado_id, final_cargado=bool(fila.acto_admin_id))
            if anexos:
                self.con_anexos(n, etapa_tipo, fila)
        return n

    def nodo_concepto(self, tipo: str, motivo: Optional[str], puede_seleccionar: bool) -> dict:
        c = self.e.concepto(tipo)
        n = self.base(f"concepto_{tipo}", ETIQUETAS_CONCEPTO[tipo], "concepto_tecnico", c)
        n["tipo"] = tipo
        if c is None:
            self.bloquear(n, motivo)
            if n["habilitada"] and puede_seleccionar and tipo != "etapa2":
                n["acciones_disponibles"].append("seleccionar_tecnico")
            return self.cerrar(n)
        n["tecnico"] = self.persona(c.tecnico_encargado_id)
        n["datos"] = {
            "fecha_visita_tecnica": _iso(c.fecha_visita_tecnica),
            "fecha_aceptacion": _iso(c.fecha_aceptacion),
            "caudal_fuente": c.caudal_fuente,
            "caudal_disponible": c.caudal_disponible,
            "caudal_otorgado": c.caudal_otorgado,
            "num_usuarios": c.num_usuarios,
            "cumple": c.cumple,
            "doc_concepto_tecnico_id": c.doc_concepto_tecnico_id,
        }
        self.con_proceso(n, "concepto_tecnico", c.id, c.tecnico_encargado_id,
                         final_cargado=bool(c.doc_concepto_tecnico_id))
        self.con_anexos(n, "concepto_tecnico", c)
        return self.cerrar(n)

    def nodo_radicado(
        self, codigo: str, etiqueta: str, etapa_tipo: str, fila, datos: dict, motivo: Optional[str],
        codigo_crear: Optional[str],
    ) -> dict:
        """Documento del usuario (planos, subsanación, informe): radicado + PDF."""
        n = self.base(codigo, etiqueta, etapa_tipo, fila)
        n["datos"] = datos
        self.bloquear(n, motivo)
        if fila is None and n["habilitada"] and self.gestor and codigo_crear:
            n["acciones_disponibles"].append(codigo_crear)
        self.con_anexos(n, etapa_tipo, fila)
        return n

    # ─────────────────────────────────────────────────────────── etapas
    def admite(self) -> dict:
        f = self.e.admite
        enc = f.encargado_acto_id if f else None
        n = self.nodo_acto("admite", ETIQUETAS_ETAPA["admite"], "acto_admite", f, enc, None, asignable=f is None, datos={
            "doc_oficio_alcaldia_id": f.doc_oficio_alcaldia_id if f else None,
            "doc_fijacion_aviso_id": f.doc_fijacion_aviso_id if f else None,
            "doc_constancia_fijacion_aviso_id": f.doc_constancia_fijacion_aviso_id if f else None,
        })
        if f is not None and f.acto_admin_id and (self.es_yo(enc) or self.u.super_gestion):
            n["acciones_disponibles"] += ["cargar_oficio_alcaldia", "cargar_fijacion_aviso", "cargar_constancia_fijacion"]
        return self.cerrar(n)

    def requerimiento_hijo(self, ambito: str, motivo: Optional[str]) -> dict:
        r = self.e.requerimiento(ambito)
        enc = r.encargado_acto_id if r else None
        n = self.nodo_acto(f"requerimiento_{ambito}", ETIQUETAS_REQUERIMIENTO[ambito], "requerimiento", r, enc, motivo,
                           asignable=r is None)
        n["ambito"] = ambito
        return self.cerrar(n)

    def requerimiento(self) -> dict:
        e = self.e
        r = e.req3
        n = self.requerimiento_hijo("etapa3", V.v6_requerimiento(e))
        n["codigo"] = "requerimiento"
        n["datos"] = {
            "radicado_oficio_entrada": r.radicado_oficio_entrada if r else None,
            "fecha_oficio_entrada": _iso(r.fecha_oficio_entrada) if r else None,
            "doc_oficio_entrada_id": r.doc_oficio_entrada_id if r else None,
        }
        if r is not None and r.acto_admin_id and (self.es_yo(r.encargado_acto_id) or self.u.super_gestion):
            n["acciones_disponibles"].append("registrar_respuesta")
        puede = self.gestor and r is not None and (self.u.super_gestion or self.es_yo(r.encargado_acto_id))
        n["concepto_adicional"] = self.nodo_concepto("adicional", V.flujo_concepto_adicional(e), puede)
        return n

    def decision(self) -> dict:
        e = self.e
        d = e.decision
        enc = d.encargado_acto_id if d else None
        n = self.nodo_acto("decision", ETIQUETAS_ETAPA["decision"], "decision", d, enc, V.v7_decision(e),
                           asignable=d is None, datos={
            "decision": _valor(d.decision) if d else None,
            "requiere_memorias": d.requiere_memorias if d else None,
            "fecha_ejecutoria": _iso(d.fecha_ejecutoria) if d else None,
        })
        if d is not None and d.acto_admin_id and (self.es_yo(enc) or self.u.super_gestion):
            n["acciones_disponibles"].append("registrar_ejecutoria")
        self.cerrar(n)

        r = e.recurso
        if r is None:
            motivo = V.v13_recurso(e)
            rec = self.nodo_acto("recurso", "Recurso de reposición", "recurso_reposicion", None, None, motivo,
                                 codigo_crear="crear_recurso")
        else:
            rec = self.nodo_acto("recurso", "Recurso de reposición", "recurso_reposicion", r, r.encargado_acto_id, None)
        rec["datos"] = {
            "radicado": r.radicado if r else None,
            "fecha_radicado": _iso(r.fecha_radicado) if r else None,
            "doc_recurso_id": r.doc_recurso_id if r else None,
            "resultado": _valor(r.resultado) if r else None,
        }
        n["recurso"] = self.cerrar(rec)
        return n

    def aprobacion(self, codigo: str, etiqueta: str, etapa_tipo: str, fila, motivo: Optional[str]) -> dict:
        """Acto que aprueba memorias / obras: vive en la fila de la etapa (su
        ``encargado_acto_id`` / ``acto_admin_id``); "existe" desde que alguien se asigna."""
        enc = fila.encargado_acto_id if fila else None
        n = self.nodo_acto(codigo, etiqueta, etapa_tipo, fila, enc, motivo, existe=enc is not None, anexos=False)
        return self.cerrar(n)

    def memorias(self) -> dict:
        e = self.e
        m = e.memorias
        n = self.nodo_radicado("memorias", ETIQUETAS_ETAPA["memorias"], "memorias_calculo", m, {
            "radicado": m.radicado if m else None,
            "fecha_radicado": _iso(m.fecha_radicado) if m else None,
            "doc_planos_id": m.doc_planos_id if m else None,
        }, V.v9_memorias(e), "registrar_planos")
        self.cerrar(n)
        n["concepto"] = self.nodo_concepto("memorias", V.flujo_concepto_memorias(e), self.gestor)
        n["requerimiento"] = self.requerimiento_hijo(
            "memorias", V.flujo_concepto_memorias(e) or V.v11_requerimiento_memorias(e))
        s = e.subsanacion
        sub = self.nodo_radicado("subsanacion", "Subsanación (planos ajustados)", "subsanacion", s, {
            "radicado": s.radicado if s else None,
            "fecha_radicado": _iso(s.fecha_radicado) if s else None,
            "doc_planos_ajustados_id": s.doc_planos_ajustados_id if s else None,
        }, V.flujo_concepto_memorias(e) or V.flujo_subsanacion(e), "registrar_subsanacion")
        self.cerrar(sub)
        sub["concepto"] = self.nodo_concepto("subsanacion", V.flujo_concepto_subsanacion(e), self.gestor)
        n["subsanacion"] = sub
        n["aprobacion"] = self.aprobacion("aprobacion_memorias", "Acto que aprueba las memorias", "memorias_calculo",
                                          m, V.v12_aprueba_memorias(e))
        return n

    def _informe(self, codigo: str, etiqueta: str, informe, motivo, codigo_crear) -> dict:
        n = self.nodo_radicado(codigo, etiqueta, "informe_usuario", informe, {
            "radicado": informe.radicado if informe else None,
            "fecha_radicado": _iso(informe.fecha_radicado) if informe else None,
            "doc_informe_usuario_id": informe.doc_informe_usuario_id if informe else None,
        }, motivo, codigo_crear)
        return self.cerrar(n)

    def obras(self) -> dict:
        e = self.e
        o = e.obras
        inf = e.informe_obras
        n = self.nodo_radicado("obras", ETIQUETAS_ETAPA["obras"], "recibo_satisfaccion_obras", o, {
            "informe_usuario_id": o.informe_usuario_id if o else None,
            "radicado": inf.radicado if inf else None,
            "fecha_radicado": _iso(inf.fecha_radicado) if inf else None,
            "doc_informe_usuario_id": inf.doc_informe_usuario_id if inf else None,
        }, V.v10_obras(e), "registrar_informe_usuario")
        self.cerrar(n)
        sin_obras = V.flujo_concepto_obras(e)
        n["informe"] = self._informe("informe_usuario", "Informe del usuario", inf, sin_obras, None)
        n["concepto"] = self.nodo_concepto("obras", sin_obras, self.gestor)
        n["requerimiento"] = self.requerimiento_hijo("obras", sin_obras or V.v11_requerimiento_obras(e))
        n["nuevo_informe"] = self._informe("nuevo_informe_usuario", "Nuevo informe del usuario", e.nuevo_informe_obras,
                                           sin_obras or V.flujo_nuevo_informe(e), "registrar_nuevo_informe")
        n["concepto_segundo"] = self.nodo_concepto("obras_segundo", V.flujo_concepto_obras_segundo(e), self.gestor)
        n["aprobacion"] = self.aprobacion("aprobacion_obras", "Acto que aprueba la obra", "recibo_satisfaccion_obras",
                                          o, V.v12_aprueba_obras(e))
        return n

    def terceros(self, vinculos: list[dict]) -> list[dict]:
        filas = {v.id: v for v in self.e.terceros}
        res = []
        for d in vinculos:
            fila = filas.get(d["id"])
            if fila is None:
                continue
            p = self.proceso_de("expediente_involucrado", fila.id)
            enc = p.creador_id if p else None
            n = dict(d)
            n.update({
                "codigo": "tercero", "etiqueta": "Tercero interviniente", "etapa_tipo": "expediente_involucrado",
                "existe": True, "habilitada": True, "motivos_bloqueo": [], "encargado": self.persona(enc),
                "proceso": None, "acto": None, "anexos": [], "acciones_disponibles": [],
            })
            acc = n["acciones_disponibles"]
            if self.gestor:
                acc.append("editar_representante")
                if p is None and not fila.acto_admin_id:
                    acc += ["asignarme", "desvincular"]
            n["acto"] = self.acto(fila.acto_admin_id, "expediente_involucrado", fila.id, enc)
            self.con_proceso(n, "expediente_involucrado", fila.id, enc, final_cargado=bool(fila.acto_admin_id))
            res.append(self.cerrar(n))
        return res


async def _precargar(db: AsyncSession, lector: _Lector, permisos: frozenset[str]) -> None:
    e = lector.e
    filas = e.filas()
    pares = [(t, i) for t in ETAPAS_CON_PROCESO for i in filas.get(t, ())]
    lector.procesos = await procesos_vigentes(db, pares)
    lector.resumenes = await resumenes_procesos(db, lector.procesos.values(), lector.u.user_id, permisos)

    condiciones = [and_(DocumentoAnexo.etapa_tipo == t, DocumentoAnexo.etapa_ref_id.in_(ids))
                   for t, ids in filas.items() if ids]
    if condiciones:
        anexos = (await db.execute(
            select(DocumentoAnexo).where(or_(*condiciones))
            .order_by(DocumentoAnexo.fecha_subida, DocumentoAnexo.id)
        )).scalars().all()
        for a in anexos:
            lector.anexos.setdefault((a.etapa_tipo, a.etapa_ref_id), []).append({
                "id": a.id, "etapa_tipo": a.etapa_tipo, "etapa_ref_id": a.etapa_ref_id, "nombre": a.nombre,
                "documento_anexo_id": a.documento_anexo_id, "fecha_subida": _iso(a.fecha_subida),
            })

    acto_ids = list(e.actos)
    if acto_ids:
        coms = (await db.execute(
            select(Comunicacion).where(Comunicacion.acto_administrativo_id.in_(acto_ids))
        )).scalars().all()
        lector.comunicaciones = {c.acto_administrativo_id: c for c in coms}
        notifs = (await db.execute(
            select(Notificacion).where(Notificacion.acto_admin_id.in_(acto_ids)).order_by(Notificacion.id)
        )).scalars().all()
        for n in notifs:
            lector.notificaciones.setdefault(n.acto_admin_id, []).append(n)

    ids: set[int] = set()
    for f in (e.admite, e.req3, e.decision, e.recurso, e.memorias, e.obras, *e.requerimientos.values()):
        if f is not None and f.encargado_acto_id:
            ids.add(f.encargado_acto_id)
    ids |= {c.tecnico_encargado_id for c in e.conceptos.values() if c.tecnico_encargado_id}
    ids |= {p.creador_id for p in lector.procesos.values() if p.creador_id}
    if ids:
        info = await users_svc.get_user_info(sorted(ids))
        lector.nombres = {int(k): (v or {}).get("nombre") for k, v in (info or {}).items()}


def etapa_actual(e: Estado) -> Optional[str]:
    """Código de la etapa más avanzada que existe según el orden del plan §4."""
    existentes = {
        "admite": e.admite, "concepto": e.concepto2, "requerimiento": e.req3,
        "decision": e.decision, "memorias": e.memorias, "obras": e.obras,
    }
    actuales = [c for c, fila in existentes.items() if fila is not None]
    return max(actuales, key=ORDEN_ETAPAS.__getitem__) if actuales else None


async def leer_etapas(db: AsyncSession, expediente: Expediente, usuario: Usuario) -> dict:
    e = await cargar_estado(db, expediente)
    permisos = await permisos_de_usuario(
        usuario.user_id, (*PERMISOS_REVISOR, Permission.MANAGE, Permission.TECNICO),
    )
    lector = _Lector(e, usuario, permisos)
    await _precargar(db, lector, permisos)
    vinculos_terceros = await serializar_vinculos(db, expediente.id, TipoVinculo.TERCERO_INTERVINIENTE)

    actual = etapa_actual(e)
    return {
        "etapa_actual": actual,
        "etapa_actual_etiqueta": ETIQUETAS_ETAPA.get(actual) if actual else None,
        "orden": list(ORDEN_ETAPAS),
        "acciones_disponibles": ["vincular_tercero"] if lector.gestor else [],
        "admite": lector.admite(),
        "concepto": lector.nodo_concepto("etapa2", V.v5_concepto_etapa2(e), False),
        "requerimiento": lector.requerimiento(),
        "decision": lector.decision(),
        "memorias": lector.memorias(),
        "obras": lector.obras(),
        "terceros": lector.terceros(vinculos_terceros),
    }
