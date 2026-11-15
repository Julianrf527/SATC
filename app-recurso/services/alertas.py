"""Alertas de vencimiento de Concesiones de Aguas (pestaña Alertas).

Se calculan al vuelo (sin tabla), igual que en infraction, con el mismo
formato de alerta y semáforo para reutilizar ``satc_shared.alertas`` y la
feature ``alertas`` del frontend. Los plazos son en días hábiles (Colombia:
sin sábados, domingos ni festivos) salvo los del recurso de reposición, que
son en días calendario.

Reglas (cada alerta vive solo mientras su hito no se cumple y solo sobre el
proceso de revisión ACTIVO de la etapa; las devoluciones no reinician el
conteo):

Auto que admite (proceso ``AUTO_ADMITE``)
  - ``admite_primera_version``: 4 días desde que nace el proceso (encargado
    asignado) hasta que existe la versión 1.
  - ``admite_revision``: 3 días desde la versión 1 hasta "aprobado para firma".
  - ``admite_version_final``: 3 días desde "aprobado para firma" hasta que se
    carga el acto (``acto_admite.acto_admin_id``).
  - ``admite_aviso_publicado``: informativa; cuenta los 10 días del aviso desde
    que se registra la comunicación del auto y desaparece al cumplirlos.

Concepto técnico de la etapa 2 (proceso ``CONCEPTO_ETAPA2``)
  - ``concepto_primera_version``: 16 días desde la fecha de visita técnica
    hasta que existe la versión 1.
  - ``concepto_version_final``: 5 días desde la versión 1 hasta que se carga
    la versión final (``concepto_tecnico.doc_concepto_tecnico_id``).

Acto del requerimiento de la etapa 3 (proceso ``REQUERIMIENTO``; solo si el
concepto de la etapa 2 no dice ``DECIDE``)
  - ``requerimiento_primera_version``: 6 días desde la versión final del
    concepto de la etapa 2 hasta la versión 1 (corre aunque nadie se haya
    asignado el requerimiento).
  - ``requerimiento_revision``: 4 días desde la versión 1 hasta "aprobado para firma".
  - ``requerimiento_version_final``: 2 días desde "aprobado para firma" hasta
    que se carga el acto.

Concepto técnico adicional (proceso ``CONCEPTO_ADICIONAL``)
  - ``concepto_adicional_tecnico``: 5 días desde que se registra la respuesta
    del usuario al requerimiento hasta que se asigna el técnico.
  - ``concepto_adicional_primera_version``: 5 días desde la asignación del
    técnico hasta la versión 1.
  - ``concepto_adicional_revision``: 2 días desde la versión 1 hasta "aprobado para firma".
  - ``concepto_adicional_version_final``: 1 día desde "aprobado para firma"
    hasta la versión final.

Acto de decisión (proceso ``DECISION``)
  - ``decision_primera_version``: 6 días desde la versión final del concepto
    adicional (o, si el concepto de la etapa 2 dice ``DECIDE``, desde la del
    concepto de la etapa 2) hasta la versión 1.
  - ``decision_revision``: 4 días; ``decision_version_final``: 2 días.

Recurso de reposición (días CALENDARIO, desde que se registra el recurso)
  - Con práctica de pruebas: ``recurso_concepto_pruebas`` (30 días hasta la
    versión final del concepto técnico de pruebas) y luego
    ``recurso_acto_tras_pruebas`` (30 días desde esa versión final hasta el
    acto que resuelve el recurso).
  - Sin práctica de pruebas: ``recurso_acto`` (60 días hasta el acto que
    resuelve el recurso).
  Si cambia «¿requiere práctica de pruebas?», se aplica la regla nueva sin
  reiniciar el conteo (siempre desde que se registró el recurso).

Los requerimientos de memorias y obras no tienen alertas (pendientes de definir).

La regla "visita técnica dentro de los 10 días hábiles siguientes al numerado
del auto" NO es una alerta de esta pestaña: es un aviso que no bloquea al
cargar el auto (``advertencia_visita``).

Cada alerta trae ``encargado_id`` (de quién es la tarea; None si aún nadie la
tomó) y ``expediente_id``. Las alertas las ve todo el que abre la pestaña; el
encargado solo decide "Mis alertas" y si el botón es Gestionar o Consultar.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Optional
from zoneinfo import ZoneInfo

import holidays
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from db.models.acto_admite import ActoAdmite
from db.models.comunicacion import Comunicacion
from db.models.concepto_tecnico import ConceptoTecnico
from db.models.documento_proceso import (
    DocumentoProceso,
    DocumentoProcesoAuditoria,
    DocumentoProcesoVersion,
)
from db.models.decision import Decision
from db.models.practica_pruebas import PracticaPruebas
from db.models.recurso_reposicion import RecursoReposicion
from db.models.requerimiento import Requerimiento

BOGOTA = ZoneInfo("America/Bogota")

TIPO_ADMITE = "AUTO_ADMITE"
TIPO_CONCEPTO = "CONCEPTO_ETAPA2"
TIPO_REQUERIMIENTO = "REQUERIMIENTO"
TIPO_ADICIONAL = "CONCEPTO_ADICIONAL"
TIPO_DECISION = "DECISION"
TIPOS_PROCESO = (TIPO_ADMITE, TIPO_CONCEPTO, TIPO_REQUERIMIENTO, TIPO_ADICIONAL, TIPO_DECISION)
ACCIONES_APROBADO_FIRMA = ("aprobar_firma", "aprobar_firma_automatico")

PLAZO_ADMITE_PRIMERA = 4
PLAZO_ADMITE_REVISION = 3
PLAZO_ADMITE_FINAL = 3
PLAZO_AVISO = 10
PLAZO_CONCEPTO_PRIMERA = 16
PLAZO_CONCEPTO_FINAL = 5
PLAZO_VISITA = 10
# (primera versión, revisión, versión final)
PLAZOS_REQUERIMIENTO = (6, 4, 2)
PLAZO_ADICIONAL_TECNICO = 5
PLAZOS_ADICIONAL = (5, 2, 1)
PLAZOS_DECISION = (6, 4, 2)
# Recurso de reposición, días calendario.
PLAZO_RECURSO_CONCEPTO_PRUEBAS = 30
PLAZO_RECURSO_TRAS_PRUEBAS = 30
PLAZO_RECURSO_SIN_PRUEBAS = 60

ETAPA_ADMITE = "Auto que admite"
ETAPA_CONCEPTO = "Concepto técnico"
ETAPA_REQUERIMIENTO = "Requerimiento"
ETAPA_ADICIONAL = "Concepto técnico adicional"
ETAPA_DECISION = "Decisión"
ETAPA_RECURSO = "Recurso de reposición"

ESTADOS_SEMAFORO = ("verde", "amarillo", "rojo", "vencido")


# ───────────────────────────────────────────────────────────── días hábiles

@lru_cache(maxsize=None)
def _festivos_anio(anio: int) -> frozenset:
    return frozenset(holidays.Colombia(years=anio).keys())


def es_habil(d: date) -> bool:
    return d.weekday() < 5 and d not in _festivos_anio(d.year)


def sumar_habiles(inicio: date, dias: int) -> date:
    """Fecha en la que se cumplen ``dias`` hábiles contados desde el día
    siguiente a ``inicio`` (el día de inicio no cuenta)."""
    actual, cuenta = inicio, 0
    while cuenta < dias:
        actual += timedelta(days=1)
        if es_habil(actual):
            cuenta += 1
    return actual


def habiles_entre(desde: date, hasta: date) -> int:
    """Días hábiles en (desde, hasta]; 0 si ``hasta <= desde``."""
    if hasta <= desde:
        return 0
    return sum(1 for i in range(1, (hasta - desde).days + 1) if es_habil(desde + timedelta(days=i)))


def fecha_local(valor) -> Optional[date]:
    """TIMESTAMPTZ → fecha en Bogotá; ``date`` tal cual; None → None."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return (valor.astimezone(BOGOTA) if valor.tzinfo else valor).date()
    return valor


def hoy_bogota() -> date:
    return datetime.now(BOGOTA).date()


# ──────────────────────────────────────────────────────────────── semáforo

def limite_plazo(inicio: date, plazo: int, calendario: bool = False) -> date:
    """Último día del plazo (el día de inicio no cuenta)."""
    return inicio + timedelta(days=plazo) if calendario else sumar_habiles(inicio, plazo)


def dias_entre(desde: date, hasta: date, calendario: bool = False) -> int:
    """Días (hábiles o calendario) en (desde, hasta]; 0 si ``hasta <= desde``."""
    if calendario:
        return max((hasta - desde).days, 0)
    return habiles_entre(desde, hasta)


def semaforo(inicio: date, plazo: int, hoy: date, calendario: bool = False) -> dict:
    """Semáforo (días hábiles o, con ``calendario``, calendario): <50 % verde,
    ≥50 % amarillo, ≥80 % rojo y, pasado el último día del plazo, vencido."""
    limite = limite_plazo(inicio, plazo, calendario)
    transcurridos = dias_entre(inicio, hoy, calendario)
    vencido = hoy > limite
    porcentaje = min(transcurridos / plazo * 100, 100) if plazo else 100
    if vencido:
        estado, urgencia, color = "vencido", "critico", "#1f2937"
    elif porcentaje >= 80:
        estado, urgencia, color = "rojo", "alta", "#ef4444"
    elif porcentaje >= 50:
        estado, urgencia, color = "amarillo", "media", "#f59e0b"
    else:
        estado, urgencia, color = "verde", "baja", "#22c55e"
    return {
        "estado": estado,
        "color_hex": color,
        "porcentaje_avance": round(porcentaje, 1),
        "urgencia": urgencia,
        "dias_transcurridos": transcurridos,
        "dias_restantes": dias_entre(hoy, limite, calendario),
        "dias_totales": plazo,
        "esta_vencido": vencido,
    }


def _alerta(tipo: str, etapa: str, accion: str, plazo_legal: str, inicio: date, plazo: int, hoy: date, *,
            expediente_id: int, encargado_id: Optional[int], msg: Optional[str] = None,
            calendario: bool = False) -> dict:
    return {
        "tipo": tipo,
        "etapa": etapa,
        "accion_requerida": accion,
        "plazo_legal": plazo_legal,
        "msg": msg or accion,
        "fecha_inicio": inicio.isoformat(),
        "fecha_limite": limite_plazo(inicio, plazo, calendario).isoformat(),
        "semaforo": semaforo(inicio, plazo, hoy, calendario),
        "expediente_id": expediente_id,
        "encargado_id": encargado_id,
    }


def _fmt(d: date) -> str:
    return d.strftime("%d/%m/%Y")


# ────────────────────────────────────────────────────────────────── reglas

@dataclass
class _Proceso:
    id: int
    expediente_id: int
    tipo_documento: str
    etapa_ref_id: int
    creador_id: Optional[int]
    fecha_creacion: date
    primera_version: Optional[date] = None
    aprobado_firma: Optional[date] = None


def _reglas_admite(p: Optional[_Proceso], admite, comunicacion: Optional[date], hoy: date) -> dict:
    alertas: dict[str, dict] = {}
    if admite is None:
        return alertas
    exp_id = admite.expediente_id

    if p is not None and admite.acto_admin_id is None:
        enc = p.creador_id
        if p.primera_version is None:
            alertas["admite_primera_version"] = _alerta(
                "admite_primera_version", ETAPA_ADMITE,
                "Cargar la primera versión del auto que admite",
                f"{PLAZO_ADMITE_PRIMERA} días hábiles desde la asignación del encargado",
                p.fecha_creacion, PLAZO_ADMITE_PRIMERA, hoy, expediente_id=exp_id, encargado_id=enc,
            )
        elif p.aprobado_firma is None:
            alertas["admite_revision"] = _alerta(
                "admite_revision", ETAPA_ADMITE,
                "Completar la revisión del auto que admite hasta aprobarlo para firma",
                f"{PLAZO_ADMITE_REVISION} días hábiles desde la primera versión",
                p.primera_version, PLAZO_ADMITE_REVISION, hoy, expediente_id=exp_id, encargado_id=enc,
            )
        else:
            alertas["admite_version_final"] = _alerta(
                "admite_version_final", ETAPA_ADMITE,
                "Cargar la versión final firmada del auto que admite",
                f"{PLAZO_ADMITE_FINAL} días hábiles desde la aprobación para firma",
                p.aprobado_firma, PLAZO_ADMITE_FINAL, hoy, expediente_id=exp_id, encargado_id=enc,
            )

    if admite.acto_admin_id is not None and comunicacion is not None:
        limite = sumar_habiles(comunicacion, PLAZO_AVISO)
        if hoy <= limite:
            dia = habiles_entre(comunicacion, hoy)
            alertas["admite_aviso_publicado"] = _alerta(
                "admite_aviso_publicado", ETAPA_ADMITE,
                f"Aviso publicado: día {dia} de {PLAZO_AVISO} hábiles",
                f"{PLAZO_AVISO} días hábiles desde el registro de la comunicación del auto",
                comunicacion, PLAZO_AVISO, hoy, expediente_id=exp_id, encargado_id=admite.encargado_acto_id,
                msg=f"El aviso lleva {dia} de {PLAZO_AVISO} días hábiles publicado (termina el {_fmt(limite)})",
            )
    return alertas


def _reglas_concepto(p: Optional[_Proceso], concepto, hoy: date) -> dict:
    alertas: dict[str, dict] = {}
    if concepto is None or concepto.doc_concepto_tecnico_id is not None:
        return alertas
    exp_id = concepto.expediente_id
    enc = p.creador_id if p is not None else concepto.tecnico_encargado_id
    primera = p.primera_version if p is not None else None

    if primera is None:
        if concepto.fecha_visita_tecnica is not None:
            alertas["concepto_primera_version"] = _alerta(
                "concepto_primera_version", ETAPA_CONCEPTO,
                "Cargar la primera versión del concepto técnico",
                f"{PLAZO_CONCEPTO_PRIMERA} días hábiles desde la visita técnica",
                concepto.fecha_visita_tecnica, PLAZO_CONCEPTO_PRIMERA, hoy, expediente_id=exp_id, encargado_id=enc,
            )
    else:
        alertas["concepto_version_final"] = _alerta(
            "concepto_version_final", ETAPA_CONCEPTO,
            "Cargar la versión final del concepto técnico",
            f"{PLAZO_CONCEPTO_FINAL} días hábiles desde la primera versión",
            primera, PLAZO_CONCEPTO_FINAL, hoy, expediente_id=exp_id, encargado_id=enc,
        )
    return alertas


def _tres_hitos(prefijo: str, etapa: str, documento: str, plazos: tuple[int, int, int], p: Optional[_Proceso],
                inicio: Optional[date], desde: str, hoy: date, *, expediente_id: int,
                encargado_id: Optional[int]) -> dict:
    """Primera versión → revisión → versión final de un documento aún sin
    versión final. Sin proceso o sin versión 1, cuenta desde ``inicio`` (si
    no hay ``inicio`` no hay alerta)."""
    primera, revision, final = plazos
    comun = {"expediente_id": expediente_id, "encargado_id": encargado_id}
    if p is None or p.primera_version is None:
        if inicio is None:
            return {}
        clave = f"{prefijo}_primera_version"
        return {clave: _alerta(clave, etapa, f"Cargar la primera versión del {documento}",
                               f"{primera} días hábiles desde {desde}", inicio, primera, hoy, **comun)}
    if p.aprobado_firma is None:
        clave = f"{prefijo}_revision"
        return {clave: _alerta(clave, etapa, f"Completar la revisión del {documento} hasta aprobarlo para firma",
                               f"{revision} días hábiles desde la primera versión", p.primera_version, revision,
                               hoy, **comun)}
    clave = f"{prefijo}_version_final"
    dias = "día hábil" if final == 1 else "días hábiles"
    return {clave: _alerta(clave, etapa, f"Cargar la versión final firmada del {documento}",
                           f"{final} {dias} desde la aprobación para firma", p.aprobado_firma, final, hoy, **comun)}


def _reglas_etapas_3_y_4(concepto, req, decision, por_etapa: dict, hoy: date) -> dict:
    """Requerimiento (etapa 3), concepto adicional y decisión (etapa 4) a
    partir del concepto de la etapa 2 (``concepto``) ya cargado."""
    alertas: dict[str, dict] = {}
    if concepto is None or concepto.doc_concepto_tecnico_id is None:
        return alertas
    exp_id = concepto.expediente_id
    final_etapa2 = fecha_local(concepto.fecha_version_final)

    if concepto.accion == "DECIDE":
        inicio_decision = final_etapa2
    else:
        # Acto del requerimiento.
        if req is None or req.acto_admin_id is None:
            alertas.update(_tres_hitos(
                "requerimiento", ETAPA_REQUERIMIENTO, "acto del requerimiento", PLAZOS_REQUERIMIENTO,
                por_etapa.get((TIPO_REQUERIMIENTO, req.id)) if req is not None else None,
                final_etapa2, "la versión final del concepto técnico de la etapa 2", hoy,
                expediente_id=exp_id, encargado_id=req.encargado_acto_id if req is not None else None,
            ))
        # Concepto técnico adicional.
        inicio_decision = None
        if req is not None and req.adicional_id is None:
            respuesta = fecha_local(req.fecha_registro_respuesta)
            if respuesta is not None:
                alertas["concepto_adicional_tecnico"] = _alerta(
                    "concepto_adicional_tecnico", ETAPA_ADICIONAL,
                    "Asignar el técnico del concepto técnico adicional",
                    f"{PLAZO_ADICIONAL_TECNICO} días hábiles desde el registro de la respuesta del usuario",
                    respuesta, PLAZO_ADICIONAL_TECNICO, hoy, expediente_id=exp_id,
                    encargado_id=req.encargado_acto_id,
                )
        elif req is not None and req.adicional_doc is None:
            p = por_etapa.get((TIPO_ADICIONAL, req.adicional_id))
            if p is not None:
                alertas.update(_tres_hitos(
                    "concepto_adicional", ETAPA_ADICIONAL, "concepto técnico adicional", PLAZOS_ADICIONAL, p,
                    p.fecha_creacion, "la asignación del técnico", hoy,
                    expediente_id=exp_id, encargado_id=req.adicional_tecnico,
                ))
        elif req is not None:
            inicio_decision = fecha_local(req.adicional_final)

    # Acto de decisión.
    if decision is None or decision.acto_admin_id is None:
        desde = ("la versión final del concepto técnico de la etapa 2" if concepto.accion == "DECIDE"
                 else "la versión final del concepto técnico adicional")
        alertas.update(_tres_hitos(
            "decision", ETAPA_DECISION, "acto de decisión", PLAZOS_DECISION,
            por_etapa.get((TIPO_DECISION, decision.id)) if decision is not None else None,
            inicio_decision, desde, hoy,
            expediente_id=exp_id, encargado_id=decision.encargado_acto_id if decision is not None else None,
        ))
    return alertas


def _reglas_recurso(d, hoy: date) -> dict:
    """Recurso de reposición (días calendario desde que se registró)."""
    if d.recurso_id is None or d.recurso_acto is not None:
        return {}
    creacion = fecha_local(d.recurso_creacion)
    comun = {"expediente_id": d.expediente_id, "calendario": True}
    acto = "Cargar la versión final del acto que resuelve el recurso de reposición"
    if not d.requiere_pruebas:
        return {"recurso_acto": _alerta(
            "recurso_acto", ETAPA_RECURSO, acto,
            f"{PLAZO_RECURSO_SIN_PRUEBAS} días calendario desde el registro del recurso",
            creacion, PLAZO_RECURSO_SIN_PRUEBAS, hoy, encargado_id=d.recurso_encargado, **comun)}
    if d.pruebas_doc is None:
        return {"recurso_concepto_pruebas": _alerta(
            "recurso_concepto_pruebas", ETAPA_RECURSO,
            "Cargar la versión final del concepto técnico de la práctica de pruebas",
            f"{PLAZO_RECURSO_CONCEPTO_PRUEBAS} días calendario desde el registro del recurso",
            creacion, PLAZO_RECURSO_CONCEPTO_PRUEBAS, hoy,
            encargado_id=d.pruebas_tecnico if d.pruebas_tecnico is not None else d.pruebas_encargado, **comun)}
    final_pruebas = fecha_local(d.pruebas_final)
    if final_pruebas is None:
        return {}
    return {"recurso_acto_tras_pruebas": _alerta(
        "recurso_acto_tras_pruebas", ETAPA_RECURSO, acto,
        f"{PLAZO_RECURSO_TRAS_PRUEBAS} días calendario desde la versión final del concepto técnico de pruebas",
        final_pruebas, PLAZO_RECURSO_TRAS_PRUEBAS, hoy, encargado_id=d.recurso_encargado, **comun)}


# ────────────────────────────────────────────────────────── carga en bloque

async def calcular_alertas(
    db: AsyncSession, hoy: date, expediente_id: Optional[int] = None,
) -> dict[int, dict[str, dict]]:
    """``{expediente_id: {clave: alerta}}`` (solo expedientes con alertas).

    Sin ``expediente_id`` calcula todos los expedientes con 7 consultas en
    total (no depende de cuántos haya); con él, las mismas 7 filtradas.
    """
    def por_exp(stmt, col):
        return stmt.where(col == expediente_id) if expediente_id is not None else stmt

    # 1. Procesos activos de las etapas con alertas por hitos de revisión.
    procesos: dict[int, _Proceso] = {}
    for r in (await db.execute(por_exp(
        select(
            DocumentoProceso.id, DocumentoProceso.expediente_id, DocumentoProceso.tipo_documento,
            DocumentoProceso.etapa_ref_id, DocumentoProceso.creador_id, DocumentoProceso.fecha_creacion,
        ).where(DocumentoProceso.activo.is_(True), DocumentoProceso.tipo_documento.in_(TIPOS_PROCESO)),
        DocumentoProceso.expediente_id,
    ))).all():
        procesos[r.id] = _Proceso(r.id, r.expediente_id, r.tipo_documento, r.etapa_ref_id, r.creador_id,
                                  fecha_local(r.fecha_creacion))

    if procesos:
        filtro = DocumentoProceso.id.in_(list(procesos))
        # 2. Fecha de la primera versión de cada proceso.
        for pid, fecha in (await db.execute(
            select(DocumentoProcesoVersion.proceso_id, func.min(DocumentoProcesoVersion.fecha_subida))
            .join(DocumentoProceso, DocumentoProceso.id == DocumentoProcesoVersion.proceso_id)
            .where(filtro).group_by(DocumentoProcesoVersion.proceso_id)
        )).all():
            procesos[pid].primera_version = fecha_local(fecha)
        # 3. Última llegada a "aprobado para firma".
        for pid, fecha in (await db.execute(
            select(DocumentoProcesoAuditoria.proceso_id, func.max(DocumentoProcesoAuditoria.fecha_accion))
            .join(DocumentoProceso, DocumentoProceso.id == DocumentoProcesoAuditoria.proceso_id)
            .where(filtro, DocumentoProcesoAuditoria.accion.in_(ACCIONES_APROBADO_FIRMA))
            .group_by(DocumentoProcesoAuditoria.proceso_id)
        )).all():
            procesos[pid].aprobado_firma = fecha_local(fecha)

    por_etapa = {(p.tipo_documento, p.etapa_ref_id): p for p in procesos.values()}

    # 4. Filas del auto que admite con la fecha de su comunicación.
    admites = (await db.execute(por_exp(
        select(
            ActoAdmite.id, ActoAdmite.expediente_id, ActoAdmite.encargado_acto_id, ActoAdmite.acto_admin_id,
            Comunicacion.fecha_creacion.label("com_creacion"), Comunicacion.fecha_envio.label("com_envio"),
        ).outerjoin(Comunicacion, Comunicacion.acto_administrativo_id == ActoAdmite.acto_admin_id),
        ActoAdmite.expediente_id,
    ))).all()

    # 5. Conceptos de la etapa 2 (los sub-procesos tienen expediente_id NULL).
    conceptos = (await db.execute(por_exp(
        select(
            ConceptoTecnico.id, ConceptoTecnico.expediente_id, ConceptoTecnico.fecha_visita_tecnica,
            ConceptoTecnico.doc_concepto_tecnico_id, ConceptoTecnico.tecnico_encargado_id,
            ConceptoTecnico.accion, ConceptoTecnico.fecha_version_final,
        ).where(ConceptoTecnico.expediente_id.isnot(None)),
        ConceptoTecnico.expediente_id,
    ))).all()

    # 6. Requerimientos de la etapa 3 con su concepto adicional (los de
    #    memorias/obras tienen expediente_id NULL y no tienen alertas).
    adicional = aliased(ConceptoTecnico)
    reqs = {r.expediente_id: r for r in (await db.execute(por_exp(
        select(
            Requerimiento.id, Requerimiento.expediente_id, Requerimiento.encargado_acto_id,
            Requerimiento.acto_admin_id, Requerimiento.fecha_registro_respuesta,
            adicional.id.label("adicional_id"), adicional.doc_concepto_tecnico_id.label("adicional_doc"),
            adicional.fecha_version_final.label("adicional_final"),
            adicional.tecnico_encargado_id.label("adicional_tecnico"),
        ).outerjoin(adicional, adicional.id == Requerimiento.concepto_tecnico_id)
        .where(Requerimiento.expediente_id.isnot(None)),
        Requerimiento.expediente_id,
    ))).all()}

    # 7. Decisiones con su recurso, práctica de pruebas y concepto de pruebas.
    pruebas = aliased(ConceptoTecnico)
    decisiones = (await db.execute(por_exp(
        select(
            Decision.id, Decision.expediente_id, Decision.encargado_acto_id, Decision.acto_admin_id,
            RecursoReposicion.id.label("recurso_id"), RecursoReposicion.fecha_creacion.label("recurso_creacion"),
            RecursoReposicion.requiere_pruebas, RecursoReposicion.acto_admin_id.label("recurso_acto"),
            RecursoReposicion.encargado_acto_id.label("recurso_encargado"),
            PracticaPruebas.encargado_acto_id.label("pruebas_encargado"),
            pruebas.doc_concepto_tecnico_id.label("pruebas_doc"), pruebas.fecha_version_final.label("pruebas_final"),
            pruebas.tecnico_encargado_id.label("pruebas_tecnico"),
        ).outerjoin(RecursoReposicion, RecursoReposicion.decision_id == Decision.id)
        .outerjoin(PracticaPruebas, PracticaPruebas.recurso_id == RecursoReposicion.id)
        .outerjoin(pruebas, pruebas.id == PracticaPruebas.concepto_tecnico_id),
        Decision.expediente_id,
    ))).all()
    dec_por_exp = {d.expediente_id: d for d in decisiones}

    resultado: dict[int, dict[str, dict]] = {}
    for a in admites:
        comunicacion = fecha_local(a.com_creacion) or a.com_envio
        alertas = _reglas_admite(por_etapa.get((TIPO_ADMITE, a.id)), a, comunicacion, hoy)
        if alertas:
            resultado.setdefault(a.expediente_id, {}).update(alertas)
    for c in conceptos:
        alertas = _reglas_concepto(por_etapa.get((TIPO_CONCEPTO, c.id)), c, hoy)
        alertas.update(_reglas_etapas_3_y_4(c, reqs.get(c.expediente_id), dec_por_exp.get(c.expediente_id),
                                            por_etapa, hoy))
        if alertas:
            resultado.setdefault(c.expediente_id, {}).update(alertas)
    for d in decisiones:
        alertas = _reglas_recurso(d, hoy)
        if alertas:
            resultado.setdefault(d.expediente_id, {}).update(alertas)
    return resultado


def estadisticas(alertas) -> dict[str, int]:
    conteo = {e: 0 for e in ESTADOS_SEMAFORO}
    for a in alertas:
        conteo[a["semaforo"]["estado"]] += 1
    return conteo


# ─────────────────────────────────────────── aviso de la fecha de visita

def limite_visita(fecha_numerado: date) -> date:
    return sumar_habiles(fecha_numerado, PLAZO_VISITA)


def advertencia_visita(fecha_numerado: Optional[date], fecha_visita: Optional[date]) -> Optional[str]:
    """Aviso (no bloquea) si la visita técnica es anterior al numerado del auto
    o posterior a los 10 días hábiles siguientes. None si está bien o falta
    alguna de las dos fechas."""
    if fecha_numerado is None or fecha_visita is None:
        return None
    if fecha_visita < fecha_numerado:
        return (f"Ojo: la fecha de visita técnica ({_fmt(fecha_visita)}) es anterior a la fecha de "
                f"numerado del auto ({_fmt(fecha_numerado)}). Verifica las fechas.")
    limite = limite_visita(fecha_numerado)
    if fecha_visita > limite:
        return (f"Ojo: la fecha de visita técnica ({_fmt(fecha_visita)}) está fuera de los {PLAZO_VISITA} días "
                f"hábiles siguientes al numerado del auto (límite {_fmt(limite)}). "
                "Esto puede afectar los indicadores.")
    return None
