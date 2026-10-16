"""Cálculo de las alertas de vencimiento de los expedientes de infracción.

Las reglas (qué genera una alerta, plazos, semáforo) son las mismas de
siempre; lo que cambia es cómo se cargan los datos: ``calcular_alertas_expedientes``
trae etapas, conceptos y notificaciones de TODOS los expedientes pedidos con
unas pocas consultas ``IN (...)`` (4 en total, sin importar cuántos expedientes)
y calcula en memoria. Antes eran 3-4 consultas por expediente.
"""
from collections import defaultdict
from datetime import date, timedelta
from functools import lru_cache
from typing import Iterable

import holidays
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.expediente import Expediente
from db.models.notificacion import Notificacion

# Tamaño de lote de los IN (...): asyncpg admite como máximo 32767 parámetros.
_LOTE = 5000


@lru_cache(maxsize=None)
def _festivos_anio(anio: int) -> frozenset:
    """Festivos de Colombia de un año, calculados una sola vez por proceso.

    Equivale al ``holidays.Colombia(years=...)`` que antes se creaba en cada
    cálculo: ese objeto se expande solo al año de la fecha consultada.
    """
    return frozenset(holidays.Colombia(years=anio).keys())


def _es_habil(d: date) -> bool:
    return d.weekday() < 5 and d not in _festivos_anio(d.year)


def fecha_limite_habiles(fecha_inicio: date, dias_habiles: int) -> date:
    count = 0
    current = fecha_inicio
    while count < dias_habiles:
        current += timedelta(days=1)
        if _es_habil(current):
            count += 1
    return current


def _build_semaforo(fecha_inicio: date, fecha_limite: date, fecha_hoy: date) -> dict:
    esta_vencido = fecha_hoy > fecha_limite
    dias_totales = max((fecha_limite - fecha_inicio).days, 1)
    dias_transcurridos = max((fecha_hoy - fecha_inicio).days, 0)
    dias_restantes = max((fecha_limite - fecha_hoy).days, 0)
    porcentaje = min((dias_transcurridos / dias_totales) * 100, 100)

    if esta_vencido:
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
        "dias_transcurridos": dias_transcurridos,
        "dias_restantes": dias_restantes,
        "dias_totales": dias_totales,
        "esta_vencido": esta_vencido,
    }


def _alerta(tipo: str, etapa: str, accion: str, plazo: str,
            fecha_inicio: date, fecha_limite: date, fecha_hoy: date, msg: str = None) -> dict:
    return {
        "tipo": tipo,
        "etapa": etapa,
        "accion_requerida": accion,
        "plazo_legal": plazo,
        "msg": msg or accion,
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_limite": fecha_limite.isoformat(),
        "semaforo": _build_semaforo(fecha_inicio, fecha_limite, fecha_hoy),
    }


def _lotes(ids: list) -> Iterable[list]:
    for i in range(0, len(ids), _LOTE):
        yield ids[i:i + _LOTE]


def _calcular(fecha_creacion: date, tiene_respuesta: bool, concepto, notifs_constancia: list,
              fecha_hoy: date) -> dict:
    """Reglas de un expediente con sus datos ya cargados (sin BD)."""
    alertas = {}

    # 1. Respuesta: 15 días hábiles desde creación del expediente
    if not tiene_respuesta:
        fecha_lim_resp = fecha_limite_habiles(fecha_creacion, 15)
        alertas["respuesta_plazo"] = _alerta(
            tipo="respuesta_plazo",
            etapa="Respuesta",
            accion="Registrar la etapa de respuesta con radicado y fecha de radicado",
            plazo="15 días hábiles desde la creación del expediente",
            fecha_inicio=fecha_creacion,
            fecha_limite=fecha_lim_resp,
            fecha_hoy=fecha_hoy,
        )

    # 2. Concepto: 15 días hábiles desde fecha_constancia_citacion (cambiar a comunicación)
    if (concepto and concepto.tipo_acogida_concepto == "AUTO_REQUERIMIENTO"
            and concepto.acto_administrativo_id):
        for notif in notifs_constancia:
            fecha_const = notif.fecha_constancia_citacion
            fecha_lim_com = fecha_limite_habiles(fecha_const, 15)
            alertas[f"concepto_constancia_{notif.id}"] = _alerta(
                tipo="concepto_constancia",
                etapa="Concepto",
                accion="Constancia de citación registrada. Si no hay notificación exitosa al vencer el plazo, cambiar a comunicación",
                plazo="15 días hábiles desde fecha de constancia de citación",
                fecha_inicio=fecha_const,
                fecha_limite=fecha_lim_com,
                fecha_hoy=fecha_hoy,
                msg=f"15 días hábiles desde constancia del {fecha_const.isoformat()} para notificar o cambiar a comunicación",
            )

    # 3. Concepto: fecha término de los días hábiles definidos
    if concepto and concepto.fecha_termino_calculada and concepto.dias_termino:
        fecha_termino = concepto.fecha_termino_calculada
        dias = concepto.dias_termino
        # Inicio estimado: regresar ~1.4 días calendario por cada día hábil
        fecha_inicio_termino = fecha_termino - timedelta(days=int(dias * 1.45))
        alertas["concepto_termino"] = _alerta(
            tipo="concepto_termino",
            etapa="Concepto",
            accion=f"El término de {dias} días hábiles del concepto técnico está en curso",
            plazo=f"{dias} días hábiles desde notificación del concepto",
            fecha_inicio=fecha_inicio_termino,
            fecha_limite=fecha_termino,
            fecha_hoy=fecha_hoy,
            msg=f"Término de {dias} días hábiles vence el {fecha_termino.isoformat()}",
        )

    return alertas


async def calcular_alertas_expedientes(
    expediente_ids: Iterable[int], db: AsyncSession, fecha_hoy: date
) -> dict[int, dict]:
    """Alertas de varios expedientes: ``{expediente_id: {clave: alerta}}``.

    Solo incluye los expedientes que existen (los que no, no aparecen, igual
    que antes devolvían ``{}``). 4 consultas en total.
    """
    ids = list(dict.fromkeys(expediente_ids))
    if not ids:
        return {}

    fechas: dict[int, date] = {}
    con_respuesta: set[int] = set()
    conceptos: dict[int, object] = {}
    for lote in _lotes(ids):
        for exp_id, fc in (await db.execute(
            select(Expediente.id, Expediente.fecha_creacion).where(Expediente.id.in_(lote))
        )).all():
            fechas[exp_id] = fc.date() if hasattr(fc, "date") else fc

        con_respuesta.update((await db.execute(
            select(EtapaRespuesta.expediente_id).where(EtapaRespuesta.expediente_id.in_(lote)).distinct()
        )).scalars().all())

        # Un concepto por expediente (el primero por id, como db.scalar antes).
        for c in (await db.execute(
            select(
                EtapaAcogerConcepto.id,
                EtapaAcogerConcepto.expediente_id,
                EtapaAcogerConcepto.tipo_acogida_concepto,
                EtapaAcogerConcepto.acto_administrativo_id,
                EtapaAcogerConcepto.fecha_termino_calculada,
                EtapaAcogerConcepto.dias_termino,
            ).where(EtapaAcogerConcepto.expediente_id.in_(lote)).order_by(EtapaAcogerConcepto.id)
        )).all():
            conceptos.setdefault(c.expediente_id, c)

    actos = list({
        c.acto_administrativo_id for c in conceptos.values()
        if c.tipo_acogida_concepto == "AUTO_REQUERIMIENTO" and c.acto_administrativo_id
    })
    notifs_por_acto: dict[int, list] = defaultdict(list)
    for lote in _lotes(actos):
        for n in (await db.execute(
            select(Notificacion.id, Notificacion.acto_administrativo_id, Notificacion.fecha_constancia_citacion)
            .where(
                Notificacion.acto_administrativo_id.in_(lote),
                Notificacion.fecha_constancia_citacion.isnot(None),
                Notificacion.notificacion_exitosa == False,  # noqa: E712 (NULL no cuenta, como antes)
            ).order_by(Notificacion.id)
        )).all():
            notifs_por_acto[n.acto_administrativo_id].append(n)

    resultado = {}
    for exp_id in ids:
        if exp_id not in fechas:
            continue
        concepto = conceptos.get(exp_id)
        notifs = notifs_por_acto.get(concepto.acto_administrativo_id, []) if concepto else []
        resultado[exp_id] = _calcular(fechas[exp_id], exp_id in con_respuesta, concepto, notifs, fecha_hoy)
    return resultado


async def calcular_alertas_expediente(expediente_id: int, db: AsyncSession, fecha_hoy: date) -> dict:
    """Alertas de un expediente (``{}`` si no existe)."""
    return (await calcular_alertas_expedientes([expediente_id], db, fecha_hoy)).get(expediente_id, {})
