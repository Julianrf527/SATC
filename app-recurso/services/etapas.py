"""Núcleo de las etapas del expediente (plan §4, fases 5–9): foto del estado,
asignación, selección de técnico y carga de la versión final.

- ``Estado`` / ``cargar_estado``: TODAS las filas de etapa del expediente en
  pocas consultas fijas (sin N+1). Lo usan las rutas (después de
  ``bloquear_expediente``) para validar §6 y ``etapas_lectura`` para pintar el
  árbol. Las reglas viven en ``services/validaciones.py`` y reciben un ``Estado``.
- Helpers de escritura (ninguno hace commit; la ruta hace ``commit`` y luego
  ``avisos.enviar()``):
  ``crear_fila_asignada`` (fila nueva con encargado → unique de la etapa),
  ``asignar_fila_existente`` (UPDATE atómico ``WHERE encargado IS NULL``),
  ``crear_concepto`` (selección de técnico, V3), ``cargar_acto_final`` y
  ``cargar_concepto_final`` (versión firmada + datos del documento).

Orden de bloqueos (como B): expediente (``FOR UPDATE``) → proceso de revisión.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Iterable, Literal, Optional

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from core.acceso import Usuario
from core.permission import Permission
from db.models import (
    ActoAdministrativo,
    ActoAdmite,
    ConceptoTecnico,
    Decision,
    Expediente,
    ExpedienteInvolucrado,
    InformeUsuario,
    MemoriasCalculo,
    ReciboSatisfaccionObras,
    RecursoReposicion,
    Requerimiento,
    Subsanacion,
    TipoActo,
    TipoVinculo,
)
from db.models.documento_proceso import DocumentoProceso
import services.docs as docs_svc
import services.users as users_svc
from services.actos import (
    _decrementar,
    _incrementar,
    acto_notificado,
    crear_acto,
    validar_fecha,
    validar_numerado,
    validar_numerado_disponible,
)
from services.concurrencia import MSG_ASIGNADO, asignar_encargado, integridad_a_409
from services.expediente_involucrados import datos_cliente
from services.revision_documentos import (
    Avisos,
    ReviewError,
    archivo_ref_por_id,
    cargar_version_final,
    crear_proceso,
    http_error,
    proceso_vigente,
)
from utils.log import insert_log

logger = logging.getLogger(__name__)

MSG_NO_ENCARGADO = "Solo el encargado de este proceso puede gestionarlo (V2)"
MSG_YA_TIENE_ACTO = "Esta etapa ya tiene su acto administrativo firmado y numerado"
MSG_SIN_PROCESO = "La etapa no tiene un proceso de revisión vigente. Recarga"
MSG_NO_TECNICO = "El usuario elegido no tiene el permiso de técnico (recurso_tecnico) (V3)"
MSG_NO_ABOGADO = "El usuario elegido no tiene el permiso de abogado (recurso_gestionar)"
MSG_SOLO_TECNICO = "Solo el técnico seleccionado puede cargar este concepto (V3)"

# ───────────────────────────────────────────────────────── catálogos de C

# Sub-procesos de concepto técnico: slug de la URL → tipo_documento (cadena de B).
TIPOS_CONCEPTO: dict[str, str] = {
    "etapa2": "CONCEPTO_ETAPA2",
    "adicional": "CONCEPTO_ADICIONAL",
    "memorias": "CONCEPTO_MEMORIAS",
    "subsanacion": "CONCEPTO_SUBSANACION",
    "obras": "CONCEPTO_OBRAS",
    "obras_segundo": "CONCEPTO_OBRAS_SEGUNDO",
}

ETIQUETAS_CONCEPTO: dict[str, str] = {
    "etapa2": "Etapa 2 · Concepto técnico",
    "adicional": "Concepto técnico adicional",
    "memorias": "Concepto técnico de memorias",
    "subsanacion": "Concepto técnico de la subsanación",
    "obras": "Concepto técnico de obras",
    "obras_segundo": "Segundo concepto técnico de obras",
}

# tipo de concepto → (atributo del padre en Estado, columna del padre que lo referencia).
PADRES_CONCEPTO: dict[str, tuple[str, str]] = {
    "adicional": ("req3", "concepto_tecnico_id"),
    "memorias": ("memorias", "concepto_tecnico_id"),
    "subsanacion": ("subsanacion", "concepto_tecnico_id"),
    "obras": ("obras", "concepto_tecnico_id"),
    "obras_segundo": ("obras", "concepto_tecnico_segundo_id"),
}

# ─── Campos que el técnico diligencia en cada concepto (UNA sola fuente) ───
# La usan la validación de "Cargar versión final" (routes/etapa_concepto.py),
# GET /etapas/conceptos/{id} (Mis informes) y el nodo de concepto del árbol
# GET /etapas/{exp} (services/etapas_lectura.py). El front arma sus formularios
# con ``definicion_campos_concepto`` y no guarda copia.
# TODO(negocio): plan §4-Etapa 2 — confirmar si los 4 datos de caudal son suficientes.
# TODO(negocio): el concepto adicional es "igual al de la etapa 2 pero sin visita"; sus
# caudales quedan opcionales porque el plan no dice si se vuelven a registrar.
CAUDALES = ("caudal_fuente", "caudal_disponible", "caudal_otorgado", "num_usuarios")

# tipo de concepto → (campos permitidos, obligatorios), además de file_id y fecha_aceptacion.
CAMPOS_CONCEPTO: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "etapa2": (CAUDALES, CAUDALES),
    "adicional": (CAUDALES, ()),
    "memorias": (("cumple",), ("cumple",)),
    "subsanacion": (("cumple",), ("cumple",)),
    "obras": (("cumple", "fecha_visita_tecnica"), ("cumple", "fecha_visita_tecnica")),
    "obras_segundo": (("cumple", "fecha_visita_tecnica"), ("cumple", "fecha_visita_tecnica")),
}

# campo → (tipo de dato para el formulario, etiqueta). Tipos: fecha | decimal | entero | si_no.
DEF_CAMPO_CONCEPTO: dict[str, tuple[str, str]] = {
    "fecha_aceptacion": ("fecha", "Fecha del concepto (firma)"),
    "fecha_visita_tecnica": ("fecha", "Fecha de visita técnica"),
    "caudal_fuente": ("decimal", "Caudal fuente (L/s)"),
    "caudal_disponible": ("decimal", "Caudal disponible (L/s)"),
    "caudal_otorgado": ("decimal", "Caudal otorgado (L/s)"),
    "num_usuarios": ("entero", "Número de usuarios"),
    "cumple": ("si_no", "¿Cumple?"),
}

# Nombres en los mensajes de error ("Faltan datos del concepto: ...").
NOMBRES_CAMPO = {
    "caudal_fuente": "caudal fuente", "caudal_disponible": "caudal disponible",
    "caudal_otorgado": "caudal otorgado", "num_usuarios": "número de usuarios",
    "cumple": "cumple / no cumple", "fecha_visita_tecnica": "fecha de visita técnica",
}


def definicion_campos_concepto(tipo: str) -> dict:
    """Definición de los campos del concepto ``tipo`` para el front::

        {"obligatorios": ["file_id", "fecha_aceptacion", ...],
         "opcionales": [...],
         "campos": [{"campo", "tipo", "etiqueta", "obligatorio"}, ...]}

    ``obligatorios``/``opcionales`` incluyen ``file_id`` (el PDF firmado);
    ``campos`` son solo los datos (sin el archivo), en orden de pantalla."""
    permitidos, obligatorios = CAMPOS_CONCEPTO[tipo]
    datos = ("fecha_aceptacion", *permitidos)
    oblig = {"fecha_aceptacion", *obligatorios}
    return {
        "obligatorios": ["file_id", "fecha_aceptacion", *obligatorios],
        "opcionales": [c for c in permitidos if c not in obligatorios],
        "campos": [
            {"campo": c, "tipo": DEF_CAMPO_CONCEPTO[c][0], "etiqueta": DEF_CAMPO_CONCEPTO[c][1],
             "obligatorio": c in oblig}
            for c in datos
        ],
    }


# Ámbitos del requerimiento: etapa 3 (directa) o sub-proceso de memorias/obras.
AMBITOS_REQUERIMIENTO = ("etapa3", "memorias", "obras")

ETIQUETAS_REQUERIMIENTO: dict[str, str] = {
    "etapa3": "Etapa 3 · Requerimiento",
    "memorias": "Requerimiento de memorias",
    "obras": "Requerimiento de obras",
}

# etapa_tipo (= nombre de tabla) válidos para documentos anexos; los mismos que
# usa la descarga del expediente (services/expediente_documentos.py).
# Todas las filas de etapa de un expediente (anexos, procesos, pertenencia).
ETAPA_TIPOS = (
    "acto_admite", "expediente_involucrado", "concepto_tecnico", "requerimiento", "decision",
    "recurso_reposicion", "memorias_calculo", "subsanacion", "recibo_satisfaccion_obras", "informe_usuario",
)
# Filas que admiten documentos anexos: todas menos el tercero interviniente
# (expediente_involucrado), que no lleva anexos (aclaración del área, 13/10/2026).
ETAPA_TIPOS_ANEXO = tuple(t for t in ETAPA_TIPOS if t != "expediente_involucrado")


# ─────────────────────────────────────────────────────────────── esquemas

class ActoFinalIn(BaseModel):
    """Datos que vienen escritos en el acto firmado (plan §4-E.3)."""

    file_id: int = Field(..., gt=0, description="PDF firmado ya subido a app-docs")
    clase_acto: Literal["AUTO", "RES"] = Field(..., description="Auto o Resolución (lo elige quien carga)")
    numerado: int | str = Field(..., description="Número del acto (máx. 4 dígitos)")
    fecha_numerado: date


class RadicadoIn(BaseModel):
    """Radicado de un documento del usuario (planos, subsanación, informe, recurso)."""

    radicado: str = Field(..., min_length=1, max_length=15)
    fecha_radicado: date
    file_id: int = Field(..., gt=0, description="PDF ya subido a app-docs")


class TecnicoIn(BaseModel):
    tecnico_id: int = Field(..., gt=0, description="id de app-users con recurso_tecnico")


def ok(message: str, data: Any = None, status_code: int = 200):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content=jsonable_encoder({"ok": True, "message": message, "data": data}), status_code=status_code,
    )


# ─────────────────────────────────────────────────────────────── estado

@dataclass
class Estado:
    """Foto de todas las filas de etapa de un expediente."""

    expediente: Expediente
    admite: Optional[ActoAdmite] = None
    concepto2: Optional[ConceptoTecnico] = None
    req3: Optional[Requerimiento] = None
    decision: Optional[Decision] = None
    recurso: Optional[RecursoReposicion] = None
    memorias: Optional[MemoriasCalculo] = None
    subsanacion: Optional[Subsanacion] = None
    obras: Optional[ReciboSatisfaccionObras] = None
    vinculos: list[ExpedienteInvolucrado] = field(default_factory=list)
    conceptos: dict[int, ConceptoTecnico] = field(default_factory=dict)
    requerimientos: dict[int, Requerimiento] = field(default_factory=dict)
    informes: dict[int, InformeUsuario] = field(default_factory=dict)
    actos: dict[int, ActoAdministrativo] = field(default_factory=dict)
    decision_notificada: bool = False

    # ---------------------------------------------------------- accesos
    def _concepto(self, cid: Optional[int]) -> Optional[ConceptoTecnico]:
        return self.conceptos.get(cid) if cid else None

    def _req(self, rid: Optional[int]) -> Optional[Requerimiento]:
        return self.requerimientos.get(rid) if rid else None

    @property
    def terceros(self) -> list[ExpedienteInvolucrado]:
        return [v for v in self.vinculos if v.tipo_vinculo == TipoVinculo.TERCERO_INTERVINIENTE]

    def concepto(self, tipo: str) -> Optional[ConceptoTecnico]:
        """Concepto por slug de ``TIPOS_CONCEPTO``."""
        if tipo == "etapa2":
            return self.concepto2
        if tipo == "adicional":
            return self._concepto(self.req3.concepto_tecnico_id) if self.req3 else None
        if tipo == "memorias":
            return self._concepto(self.memorias.concepto_tecnico_id) if self.memorias else None
        if tipo == "subsanacion":
            return self._concepto(self.subsanacion.concepto_tecnico_id) if self.subsanacion else None
        if tipo == "obras":
            return self._concepto(self.obras.concepto_tecnico_id) if self.obras else None
        if tipo == "obras_segundo":
            return self._concepto(self.obras.concepto_tecnico_segundo_id) if self.obras else None
        raise HTTPException(status_code=404, detail=f"Tipo de concepto desconocido: {tipo}")

    def requerimiento(self, ambito: str) -> Optional[Requerimiento]:
        if ambito == "etapa3":
            return self.req3
        if ambito == "memorias":
            return self._req(self.memorias.requerimiento_id) if self.memorias else None
        if ambito == "obras":
            return self._req(self.obras.requerimiento_id) if self.obras else None
        raise HTTPException(status_code=404, detail=f"Requerimiento desconocido: {ambito}")

    @property
    def informe_obras(self) -> Optional[InformeUsuario]:
        return self.informes.get(self.obras.informe_usuario_id) if self.obras else None

    @property
    def nuevo_informe_obras(self) -> Optional[InformeUsuario]:
        if not self.obras or not self.obras.nuevo_informe_usuario_id:
            return None
        return self.informes.get(self.obras.nuevo_informe_usuario_id)

    def acto(self, acto_id: Optional[int]) -> Optional[ActoAdministrativo]:
        return self.actos.get(acto_id) if acto_id else None

    def ultimo_concepto_memorias(self) -> Optional[ConceptoTecnico]:
        """Concepto de la subsanación si existe; si no, el de memorias (V12)."""
        return self.concepto("subsanacion") or self.concepto("memorias")

    def ultimo_concepto_obras(self) -> Optional[ConceptoTecnico]:
        return self.concepto("obras_segundo") or self.concepto("obras")

    def filas(self) -> dict[str, set[int]]:
        """{etapa_tipo: ids} de todas las filas del expediente (anexos y procesos)."""
        res: dict[str, set[int]] = {t: set() for t in ETAPA_TIPOS}
        for t, fila in (
            ("acto_admite", self.admite), ("decision", self.decision), ("recurso_reposicion", self.recurso),
            ("memorias_calculo", self.memorias), ("subsanacion", self.subsanacion),
            ("recibo_satisfaccion_obras", self.obras),
        ):
            if fila is not None:
                res[t].add(fila.id)
        res["concepto_tecnico"].update(self.conceptos)
        res["requerimiento"].update(self.requerimientos)
        res["informe_usuario"].update(self.informes)
        res["expediente_involucrado"].update(v.id for v in self.terceros)
        return res

    def pertenece(self, etapa_tipo: str, etapa_ref_id: int) -> bool:
        return etapa_ref_id in self.filas().get(etapa_tipo, set())


async def _una(db: AsyncSession, modelo, *condiciones):
    return await db.scalar(
        select(modelo).where(*condiciones).execution_options(populate_existing=True)
    )


async def _por_ids(db: AsyncSession, modelo, ids: Iterable[Optional[int]]) -> dict[int, Any]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    filas = (await db.execute(
        select(modelo).where(modelo.id.in_(ids)).execution_options(populate_existing=True)
    )).scalars().all()
    return {f.id: f for f in filas}


async def cargar_estado(db: AsyncSession, expediente: Expediente) -> Estado:
    """Carga todas las etapas del expediente (número fijo de consultas). En
    escrituras llamar DESPUÉS de ``bloquear_expediente``."""
    exp_id = expediente.id
    e = Estado(expediente=expediente)
    e.admite = await _una(db, ActoAdmite, ActoAdmite.expediente_id == exp_id)
    e.concepto2 = await _una(db, ConceptoTecnico, ConceptoTecnico.expediente_id == exp_id)
    e.req3 = await _una(db, Requerimiento, Requerimiento.expediente_id == exp_id)
    e.decision = await _una(db, Decision, Decision.expediente_id == exp_id)
    if e.decision is not None:
        e.recurso = await _una(db, RecursoReposicion, RecursoReposicion.decision_id == e.decision.id)
    e.memorias = await _una(db, MemoriasCalculo, MemoriasCalculo.expediente_id == exp_id)
    if e.memorias is not None and e.memorias.subsanacion_id:
        e.subsanacion = await _una(db, Subsanacion, Subsanacion.id == e.memorias.subsanacion_id)
    e.obras = await _una(db, ReciboSatisfaccionObras, ReciboSatisfaccionObras.expediente_id == exp_id)
    e.vinculos = list((await db.execute(
        select(ExpedienteInvolucrado)
        .where(ExpedienteInvolucrado.expediente_id == exp_id)
        .order_by(ExpedienteInvolucrado.fecha_vinculacion, ExpedienteInvolucrado.id)
        .execution_options(populate_existing=True)
    )).scalars().all())

    e.conceptos = await _por_ids(db, ConceptoTecnico, [
        e.req3.concepto_tecnico_id if e.req3 else None,
        e.memorias.concepto_tecnico_id if e.memorias else None,
        e.subsanacion.concepto_tecnico_id if e.subsanacion else None,
        e.obras.concepto_tecnico_id if e.obras else None,
        e.obras.concepto_tecnico_segundo_id if e.obras else None,
    ])
    if e.concepto2 is not None:
        e.conceptos[e.concepto2.id] = e.concepto2
    e.requerimientos = await _por_ids(db, Requerimiento, [
        e.memorias.requerimiento_id if e.memorias else None,
        e.obras.requerimiento_id if e.obras else None,
    ])
    if e.req3 is not None:
        e.requerimientos[e.req3.id] = e.req3
    if e.obras is not None:
        e.informes = await _por_ids(db, InformeUsuario, [e.obras.informe_usuario_id, e.obras.nuevo_informe_usuario_id])

    acto_ids = [f.acto_admin_id for f in (e.admite, e.decision, e.recurso, e.memorias, e.obras) if f is not None]
    acto_ids += [r.acto_admin_id for r in e.requerimientos.values()]
    acto_ids += [v.acto_admin_id for v in e.terceros]
    e.actos = await _por_ids(db, ActoAdministrativo, acto_ids)
    if e.decision is not None and e.decision.acto_admin_id:
        e.decision_notificada = await acto_notificado(db, e.decision.acto_admin_id)
    return e


# ─────────────────────────────────────────────────────────────── utilidades

def exigir(motivo: Optional[str], usuario: Optional[Usuario] = None, status_code: int = 400) -> None:
    """Lanza ``motivo`` (regla §6 / orden del flujo). Super gestión las omite (§2.1)."""
    if motivo and not (usuario is not None and usuario.super_gestion):
        raise HTTPException(status_code=status_code, detail=motivo)


def exigir_encargado(encargado_id: Optional[int], usuario: Usuario, *, permitir_super: bool = False) -> None:
    """V2: solo el encargado gestiona su proceso. ``permitir_super``: en
    ediciones de datos de la etapa super gestión omite la asignación (§2.1)."""
    if permitir_super and usuario.super_gestion:
        return
    if encargado_id is None or encargado_id != usuario.user_id:
        raise HTTPException(status_code=403, detail=MSG_NO_ENCARGADO)


def subir_version(fila) -> None:
    """Incrementa la ``version`` de una fila editada dentro de una transición
    (el expediente está bloqueado, así que no hay carrera)."""
    if hasattr(fila, "version"):
        fila.version = (fila.version or 1) + 1


async def validar_pdf(file_id: int, campo: str) -> None:
    """El archivo existe en app-docs y es PDF (entra a la descarga del expediente)."""
    info = await docs_svc.get_file_info(file_id)
    if not info.get("ok"):
        raise HTTPException(status_code=400, detail=f"{campo}: archivo no encontrado en el gestor documental")
    if (info["data"].get("content_type") or "").lower() != "application/pdf":
        raise HTTPException(status_code=400, detail=f"{campo}: debe ser un PDF")


async def registrar_archivos(nuevos: Iterable[Optional[int]]) -> None:
    """``numero_usos`` +1 (antes del commit; 502 si app-docs falla)."""
    await _incrementar([f for f in nuevos if f])


async def liberar_archivos(anteriores: Iterable[Optional[int]]) -> None:
    """``numero_usos`` −1 (después del commit, best-effort)."""
    await _decrementar([f for f in anteriores if f])


async def auditar(
    db: AsyncSession, usuario: Usuario, expediente: Expediente, tipo_evento: str, detalle: str,
    datos: Optional[dict] = None, request: Optional[Request] = None,
) -> None:
    await insert_log(
        db=db, tipo_evento=tipo_evento[:30], resultado="EXITOSO", usuario_id=usuario.user_id,
        expediente_id=expediente.id, expediente_radicado=expediente.radicado, detalle=detalle,
        datos_nuevos=jsonable_encoder(datos) if datos else None, **datos_cliente(request),
    )


async def es_tecnico(user_id: int) -> bool:
    return await users_svc.verify_permission(user_id, Permission.TECNICO)


async def exigir_tecnico(user_id: Optional[int], actual: Optional[int] = None) -> None:
    """La persona ELEGIDA como técnico encargado tiene ``recurso_tecnico``
    (mismo criterio que ``GET /etapas/tecnicos``). 400 si no; fail-closed (si
    app-users falla, se rechaza). ``actual``: valor que ya tenía la fila (no se
    revalida si no cambia). Aplica también a super gestión: elegir a alguien sin
    el permiso lo dejaría a cargo sin poder trabajar."""
    if user_id and user_id != actual and not await es_tecnico(user_id):
        raise HTTPException(status_code=400, detail=MSG_NO_TECNICO)


async def exigir_abogado(user_id: Optional[int], actual: Optional[int] = None) -> None:
    """La persona ELEGIDA como abogado encargado tiene ``recurso_gestionar``
    (mismo criterio que ``GET /etapas/abogados``). Igual que ``exigir_tecnico``."""
    if user_id and user_id != actual and not await users_svc.verify_permission(user_id, Permission.MANAGE):
        raise HTTPException(status_code=400, detail=MSG_NO_ABOGADO)


# ─────────────────────────────────────────────────────────── asignación

async def crear_proceso_etapa(
    db: AsyncSession, *, expediente_id: int, tipo_documento: str, etapa_tipo: str, etapa_ref_id: int,
    encargado_id: int, usuario: Usuario, avisos: Avisos,
) -> DocumentoProceso:
    try:
        return await crear_proceso(
            db, expediente_id=expediente_id, tipo_documento=tipo_documento, etapa_tipo=etapa_tipo,
            etapa_ref_id=etapa_ref_id, encargado_id=encargado_id, usuario_id=usuario.user_id, avisos=avisos,
        )
    except ReviewError as e:
        raise http_error(e)


async def crear_fila_asignada(
    db: AsyncSession, fila, *, etapa_tipo: str, tipo_documento: str, expediente_id: int,
    usuario: Usuario, avisos: Avisos, mensaje_409: str = MSG_ASIGNADO,
) -> DocumentoProceso:
    """"Asignarme para diligenciar" de una etapa que nace con el encargado
    (acto_admite, requerimiento, decisión): inserta la fila y su proceso en
    ``pendiente_carga``. El ``unique`` de la etapa resuelve la carrera (409)."""
    async with integridad_a_409(db, mensaje_409):
        db.add(fila)
        await db.flush()
        return await crear_proceso_etapa(
            db, expediente_id=expediente_id, tipo_documento=tipo_documento, etapa_tipo=etapa_tipo,
            etapa_ref_id=fila.id, encargado_id=usuario.user_id, usuario=usuario, avisos=avisos,
        )


async def asignar_fila_existente(
    db: AsyncSession, modelo: type, fila, *, etapa_tipo: str, tipo_documento: str, expediente_id: int,
    usuario: Usuario, avisos: Avisos,
) -> DocumentoProceso:
    """"Asignarme" sobre una fila que ya existe sin encargado (recurso, acto que
    aprueba memorias/obras): ``UPDATE ... WHERE encargado_acto_id IS NULL``
    (0 filas → 409 "Ya fue asignado") y crea el proceso."""
    await asignar_encargado(db, modelo, fila.id, usuario.user_id)
    fila.encargado_acto_id = usuario.user_id
    subir_version(fila)
    async with integridad_a_409(db, MSG_ASIGNADO):
        await db.flush()
        return await crear_proceso_etapa(
            db, expediente_id=expediente_id, tipo_documento=tipo_documento, etapa_tipo=etapa_tipo,
            etapa_ref_id=fila.id, encargado_id=usuario.user_id, usuario=usuario, avisos=avisos,
        )


async def enlazar_hijo(db: AsyncSession, padre, columna: str, hijo_id: int) -> None:
    """``UPDATE padre SET columna = :hijo, version = version + 1 WHERE id AND
    columna IS NULL`` (V15: un sub-proceso tiene un solo padre y cada referencia
    del padre se llena una vez). 0 filas → 409. Refleja el cambio en el objeto
    en memoria sin marcarlo sucio."""
    modelo = type(padre)
    col = getattr(modelo, columna)
    valores = {columna: hijo_id}
    if hasattr(modelo, "version"):
        valores["version"] = modelo.version + 1
    res = await db.execute(
        update(modelo).where(modelo.id == padre.id, col.is_(None))
        .values(valores).execution_options(synchronize_session=False)
    )
    if res.rowcount == 0:
        raise HTTPException(status_code=409, detail="Ya existe, otra persona lo creó al mismo tiempo. Recarga")
    set_committed_value(padre, columna, hijo_id)
    if hasattr(modelo, "version"):
        set_committed_value(padre, "version", (padre.version or 1) + 1)


async def crear_requerimiento_hijo(
    db: AsyncSession, padre, *, expediente_id: int, usuario: Usuario, avisos: Avisos,
) -> tuple[Requerimiento, DocumentoProceso]:
    """Requerimiento de memorias/obras (``expediente_id`` NULL, plan §4-D)."""
    req = Requerimiento(expediente_id=None, encargado_acto_id=usuario.user_id)
    async with integridad_a_409(db, MSG_ASIGNADO):
        db.add(req)
        await db.flush()
        await enlazar_hijo(db, padre, "requerimiento_id", req.id)
        proceso = await crear_proceso_etapa(
            db, expediente_id=expediente_id, tipo_documento="REQUERIMIENTO", etapa_tipo="requerimiento",
            etapa_ref_id=req.id, encargado_id=usuario.user_id, usuario=usuario, avisos=avisos,
        )
    return req, proceso


async def crear_concepto(
    db: AsyncSession, *, tipo: str, tecnico_id: int, expediente_id: int, usuario: Usuario, avisos: Avisos,
    padre=None, columna: Optional[str] = None,
    fecha_visita: Optional[date] = None, con_proceso: bool = True, validar_tecnico: bool = True,
) -> tuple[ConceptoTecnico, Optional[DocumentoProceso]]:
    """Selección del técnico (V3): crea la fila ``concepto_tecnico`` (etapa 2
    con ``expediente_id``; sub-procesos con NULL enlazados al padre) y su
    proceso con el técnico como encargado. ``validar_tecnico=False`` solo
    cuando quien llama YA validó el permiso (``exigir_tecnico``) antes de tocar
    app-docs."""
    if validar_tecnico:
        await exigir_tecnico(tecnico_id)
    concepto = ConceptoTecnico(
        expediente_id=expediente_id if tipo == "etapa2" else None,
        tecnico_encargado_id=tecnico_id,
        fecha_visita_tecnica=fecha_visita,
    )
    proceso = None
    async with integridad_a_409(db):
        db.add(concepto)
        await db.flush()
        if padre is not None:
            await enlazar_hijo(db, padre, columna, concepto.id)
        if con_proceso:
            proceso = await crear_proceso_etapa(
                db, expediente_id=expediente_id, tipo_documento=TIPOS_CONCEPTO[tipo], etapa_tipo="concepto_tecnico",
                etapa_ref_id=concepto.id, encargado_id=tecnico_id, usuario=usuario, avisos=avisos,
            )
    return concepto, proceso


# ───────────────────────────────────────────────────── versión final

async def preparar_acto(db: AsyncSession, tipo_acto: TipoActo, datos: ActoFinalIn) -> None:
    """Valida numerado/fecha/duplicado ANTES de tocar app-docs."""
    numero = validar_numerado(datos.numerado)
    fecha = validar_fecha(datos.fecha_numerado, "fecha de numerado")
    await validar_numerado_disponible(db, ActoAdministrativo, numero, fecha, tipo_acto=tipo_acto)


async def cargar_acto_final(
    db: AsyncSession, *, fila, etapa_tipo: str, tipo_acto: TipoActo, encargado_id: Optional[int],
    datos: ActoFinalIn, usuario: Usuario, avisos: Avisos,
) -> ActoAdministrativo:
    """"Cargar versión final" de una etapa con acto (plan §4-E.3): el encargado
    sube el PDF firmado + numerado + fecha → proceso ``aprobado`` (B) y se crea
    y enlaza el ``acto_administrativo``."""
    if fila.acto_admin_id:
        raise HTTPException(status_code=409, detail=MSG_YA_TIENE_ACTO)
    exigir_encargado(encargado_id, usuario)
    await preparar_acto(db, tipo_acto, datos)
    proceso = await proceso_vigente(db, etapa_tipo, fila.id, para_actualizar=True)
    if proceso is None:
        raise HTTPException(status_code=409, detail=MSG_SIN_PROCESO)
    ref = await archivo_ref_por_id(datos.file_id)
    try:
        await cargar_version_final(db, proceso, ref, usuario.user_id, avisos)
    except ReviewError as e:
        raise http_error(e)
    acto = await crear_acto(
        db, tipo_acto=tipo_acto, clase_acto=datos.clase_acto, numerado=datos.numerado,
        fecha_numerado=datos.fecha_numerado, documento_id=datos.file_id, user_id=usuario.user_id,
    )
    fila.acto_admin_id = acto.id
    subir_version(fila)
    await db.flush()
    return acto


async def cargar_concepto_final(
    db: AsyncSession, *, concepto: ConceptoTecnico, file_id: int, valores: dict, usuario: Usuario, avisos: Avisos,
) -> None:
    """Versión firmada del concepto (la carga el técnico seleccionado, V3) +
    datos escritos en él."""
    if concepto.doc_concepto_tecnico_id:
        raise HTTPException(status_code=409, detail="Este concepto ya tiene su versión final cargada")
    if concepto.tecnico_encargado_id != usuario.user_id:
        raise HTTPException(status_code=403, detail=MSG_SOLO_TECNICO)
    proceso = await proceso_vigente(db, "concepto_tecnico", concepto.id, para_actualizar=True)
    if proceso is None:
        raise HTTPException(status_code=409, detail=MSG_SIN_PROCESO)
    ref = await archivo_ref_por_id(file_id)
    try:
        await cargar_version_final(db, proceso, ref, usuario.user_id, avisos)
    except ReviewError as e:
        raise http_error(e)
    for k, v in valores.items():
        setattr(concepto, k, v)
    concepto.doc_concepto_tecnico_id = file_id
    subir_version(concepto)
    await db.flush()
    # Uso propio de la columna doc_concepto_tecnico_id (además del de la versión),
    # como crear_acto: si super gestión lo reemplaza luego, la versión sigue
    # contando y el cleanup de app-docs no lo borra. Si la operación falla
    # después de este +1, get_db_managed lo compensa (services/usos_archivos.py).
    await _incrementar([file_id])


def datos_fila(fila, *extra: str) -> dict:
    """``{id, version, ...extra}`` para la respuesta de una escritura."""
    if fila is None:
        return {}
    d = {"id": fila.id, "version": getattr(fila, "version", None)}
    for k in extra:
        d[k] = getattr(fila, k, None)
    return d


# ───────────────────────────────────────── contexto de etapa de un proceso

ETIQUETAS_ETAPA_PADRE: dict[str, str] = {
    "acto_admite": "Etapa 1 · Auto que admite",
    "concepto_tecnico": "Etapa 2 · Concepto técnico",
    "requerimiento": "Etapa 3 · Requerimiento",
    "decision": "Etapa 4 · Decisión",
    "memorias_calculo": "Etapa 5 · Memorias de cálculo",
    "recibo_satisfaccion_obras": "Etapa 6 · Recibo a satisfacción de obras",
    "tercero_interviniente": "Tercero interviniente",
}

# tipo_documento → (etapa_padre, sub_proceso). REQUERIMIENTO se resuelve por la fila.
_PADRE_POR_TIPO: dict[str, tuple[str, str]] = {
    "AUTO_ADMITE": ("acto_admite", "auto_admite"),
    "CONCEPTO_ETAPA2": ("concepto_tecnico", "concepto_etapa2"),
    "CONCEPTO_ADICIONAL": ("requerimiento", "concepto_adicional"),
    "DECISION": ("decision", "decision"),
    "RECURSO": ("decision", "recurso"),
    "CONCEPTO_MEMORIAS": ("memorias_calculo", "concepto_memorias"),
    "CONCEPTO_SUBSANACION": ("memorias_calculo", "concepto_subsanacion"),
    "APRUEBA_MEMORIAS": ("memorias_calculo", "aprobacion"),
    "CONCEPTO_OBRAS": ("recibo_satisfaccion_obras", "concepto_obras"),
    "CONCEPTO_OBRAS_SEGUNDO": ("recibo_satisfaccion_obras", "concepto_obras_segundo"),
    "APRUEBA_OBRAS": ("recibo_satisfaccion_obras", "aprobacion"),
    "RECONOCE_TERCERO": ("tercero_interviniente", "reconoce_tercero"),
}


def _contexto(padre: str, sub: str) -> dict:
    return {"etapa_padre": padre, "etapa_padre_etiqueta": ETIQUETAS_ETAPA_PADRE.get(padre), "sub_proceso": sub}


async def etapas_padre(db: AsyncSession, procesos: Iterable[DocumentoProceso]) -> dict[int, dict]:
    """{proceso_id: {etapa_padre, etapa_padre_etiqueta, sub_proceso}}: etapa del
    plan (pestaña del front) a la que pertenece el documento. En lote: solo los
    REQUERIMIENTO necesitan consulta (2 como máximo)."""
    procesos = list(procesos)
    req_ids = {p.etapa_ref_id for p in procesos if p.tipo_documento == "REQUERIMIENTO"}
    ambito: dict[int, str] = {}
    if req_ids:
        en_memorias = set((await db.execute(
            select(MemoriasCalculo.requerimiento_id).where(MemoriasCalculo.requerimiento_id.in_(req_ids))
        )).scalars().all())
        en_obras = set((await db.execute(
            select(ReciboSatisfaccionObras.requerimiento_id).where(ReciboSatisfaccionObras.requerimiento_id.in_(req_ids))
        )).scalars().all())
        for rid in req_ids:
            ambito[rid] = "memorias" if rid in en_memorias else "obras" if rid in en_obras else "etapa3"
    res: dict[int, dict] = {}
    for p in procesos:
        if p.tipo_documento == "REQUERIMIENTO":
            amb = ambito.get(p.etapa_ref_id, "etapa3")
            padre = {"etapa3": "requerimiento", "memorias": "memorias_calculo",
                     "obras": "recibo_satisfaccion_obras"}[amb]
            res[p.id] = _contexto(padre, f"requerimiento_{amb}")
        else:
            padre, sub = _PADRE_POR_TIPO.get(p.tipo_documento, (p.etapa_tipo, p.tipo_documento.lower()))
            res[p.id] = _contexto(padre, sub)
    return res


async def ubicar_concepto(db: AsyncSession, concepto_id: int) -> tuple[ConceptoTecnico, Expediente, Estado, str]:
    """(concepto, expediente, estado, tipo slug) de un concepto por id. 404 si no
    existe o no cuelga de ningún expediente."""
    concepto = await db.get(ConceptoTecnico, concepto_id)
    if concepto is None:
        raise HTTPException(status_code=404, detail="Concepto técnico no encontrado")
    exp_id = concepto.expediente_id or await db.scalar(
        select(DocumentoProceso.expediente_id)
        .where(DocumentoProceso.etapa_tipo == "concepto_tecnico", DocumentoProceso.etapa_ref_id == concepto_id)
        .limit(1)
    )
    expediente = await db.get(Expediente, exp_id) if exp_id else None
    if expediente is None:
        raise HTTPException(status_code=404, detail="Concepto técnico no encontrado")
    e = await cargar_estado(db, expediente)
    for tipo in TIPOS_CONCEPTO:
        c = e.concepto(tipo)
        if c is not None and c.id == concepto_id:
            return c, expediente, e, tipo
    raise HTTPException(status_code=404, detail="Concepto técnico no encontrado")
