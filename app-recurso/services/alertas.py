"""Alertas de vencimiento de Concesiones de Aguas (pestaña Alertas).

Se calculan al vuelo (sin tabla), igual que en infraction, con el mismo
formato de alerta y semáforo para reutilizar ``satc_shared.alertas`` y la
feature ``alertas`` del frontend. TODOS los plazos son en días hábiles
(Colombia: sin sábados, domingos ni festivos).

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

La regla "visita técnica dentro de los 10 días hábiles siguientes al numerado
del auto" NO es una alerta de esta pestaña: es un aviso que no bloquea al
cargar el auto (``advertencia_visita``).

Cada alerta trae ``encargado_id`` (de quién es la tarea) y ``expediente_id``.
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

from db.models.acto_admite import ActoAdmite
from db.models.comunicacion import Comunicacion
from db.models.concepto_tecnico import ConceptoTecnico
from db.models.documento_proceso import (
    DocumentoProceso,
    DocumentoProcesoAuditoria,
    DocumentoProcesoVersion,
)

BOGOTA = ZoneInfo("America/Bogota")

TIPO_ADMITE = "AUTO_ADMITE"
TIPO_CONCEPTO = "CONCEPTO_ETAPA2"
ACCIONES_APROBADO_FIRMA = ("aprobar_firma", "aprobar_firma_automatico")

PLAZO_ADMITE_PRIMERA = 4
PLAZO_ADMITE_REVISION = 3
PLAZO_ADMITE_FINAL = 3
PLAZO_AVISO = 10
PLAZO_CONCEPTO_PRIMERA = 16
PLAZO_CONCEPTO_FINAL = 5
PLAZO_VISITA = 10

ETAPA_ADMITE = "Auto que admite"
ETAPA_CONCEPTO = "Concepto técnico"

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

def semaforo(inicio: date, plazo: int, hoy: date) -> dict:
    """Semáforo en días hábiles: <50 % verde, ≥50 % amarillo, ≥80 % rojo y,
    pasado el último día del plazo, vencido."""
    limite = sumar_habiles(inicio, plazo)
    transcurridos = habiles_entre(inicio, hoy)
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
        "dias_restantes": habiles_entre(hoy, limite),
        "dias_totales": plazo,
        "esta_vencido": vencido,
    }


def _alerta(tipo: str, etapa: str, accion: str, plazo_legal: str, inicio: date, plazo: int, hoy: date, *,
            expediente_id: int, encargado_id: Optional[int], msg: Optional[str] = None) -> dict:
    return {
        "tipo": tipo,
        "etapa": etapa,
        "accion_requerida": accion,
        "plazo_legal": plazo_legal,
        "msg": msg or accion,
        "fecha_inicio": inicio.isoformat(),
        "fecha_limite": sumar_habiles(inicio, plazo).isoformat(),
        "semaforo": semaforo(inicio, plazo, hoy),
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


# ────────────────────────────────────────────────────────── carga en bloque

async def calcular_alertas(
    db: AsyncSession, hoy: date, expediente_id: Optional[int] = None,
) -> dict[int, dict[str, dict]]:
    """``{expediente_id: {clave: alerta}}`` (solo expedientes con alertas).

    Sin ``expediente_id`` calcula todos los expedientes con 5 consultas en
    total (no depende de cuántos haya); con él, las mismas 5 filtradas.
    """
    def por_exp(stmt, col):
        return stmt.where(col == expediente_id) if expediente_id is not None else stmt

    # 1. Procesos activos del auto que admite y del concepto de la etapa 2.
    procesos: dict[int, _Proceso] = {}
    for r in (await db.execute(por_exp(
        select(
            DocumentoProceso.id, DocumentoProceso.expediente_id, DocumentoProceso.tipo_documento,
            DocumentoProceso.etapa_ref_id, DocumentoProceso.creador_id, DocumentoProceso.fecha_creacion,
        ).where(DocumentoProceso.activo.is_(True), DocumentoProceso.tipo_documento.in_((TIPO_ADMITE, TIPO_CONCEPTO))),
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
        ).where(ConceptoTecnico.expediente_id.isnot(None)),
        ConceptoTecnico.expediente_id,
    ))).all()

    resultado: dict[int, dict[str, dict]] = {}
    for a in admites:
        comunicacion = fecha_local(a.com_creacion) or a.com_envio
        alertas = _reglas_admite(por_etapa.get((TIPO_ADMITE, a.id)), a, comunicacion, hoy)
        if alertas:
            resultado.setdefault(a.expediente_id, {}).update(alertas)
    for c in conceptos:
        alertas = _reglas_concepto(por_etapa.get((TIPO_CONCEPTO, c.id)), c, hoy)
        if alertas:
            resultado.setdefault(c.expediente_id, {}).update(alertas)
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
