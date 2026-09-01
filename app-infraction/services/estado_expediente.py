"""
Calcula el "estado" de un expediente: un indicador de gestión distinto de
"etapa_actual" (que solo dice cuál fue la última etapa creada). El estado
se evalúa como una pirámide de reglas de mayor a menor prioridad — se
devuelve la primera que se cumpla, o None si ninguna aplica.
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.etapa_cierre import EtapaCierre
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.informe_tecnico import InformeTecnico
from db.models.solicitud_informacion import SolicitudInformacion
from db.models.expediente_involucrado import ExpedienteInvolucrado
from db.models.notificacion import Notificacion


def _evaluar_uno(
    *,
    archivado: bool,
    cierre_acto_id: Optional[int],
    concepto,
    visita,
    seguimiento,
    notificados_actos: set,
    solicitud_concepto_ids: set,
    tiene_involucrados: bool,
) -> Optional[str]:
    if archivado:
        return "ARCHIVADO"

    if cierre_acto_id is not None and cierre_acto_id not in notificados_actos:
        return "NOTIFICAR Y/O COMUNICAR ACTO ADM DE SEGUIMIENTO"

    if seguimiento is not None:
        if seguimiento.fecha_programacion_visita is None:
            return "PARA PROGRAMAR SEGUIMIENTO"
        return "SEGUIMIENTO PROGRAMADO"

    if concepto is not None and concepto.tipo_acogida_concepto == "AUTO_REQUERIMIENTO" and concepto.acto_administrativo_id:
        if concepto.acto_administrativo_id in notificados_actos:
            return "VISITA DE SGTO A CUMPLIMIENTO"
        return "NOTIFICAR Y/O COMUNICAR ACTO ADM. ARCHIVADO"

    if concepto is not None and concepto.id in solicitud_concepto_ids and not tiene_involucrados:
        return "POR ALLEGAR INFORMACIÓN"

    if visita is not None:
        if visita.fecha_programacion_visita is None:
            return "PARA PROGRAMAR VISITA"
        if visita.fecha_aceptacion_informe is not None and concepto is None:
            return "ACOGER CONCEPTO"
        return "VISITA PROGRAMADA"

    return None


async def calcular_estados(
    db: AsyncSession,
    expediente_ids: list[int],
    archivado_map: dict[int, bool],
) -> dict[int, Optional[str]]:
    """
    Calcula el estado de una lista de expedientes en batch (sin N+1 queries).
    `archivado_map` debe traer el flag `archivado` de cada expediente (ya
    disponible en la query principal de cada endpoint consumidor).
    """
    if not expediente_ids:
        return {}

    ids = list(expediente_ids)

    cierre_rows = (await db.execute(
        select(EtapaCierre.expediente_id, EtapaCierre.acto_administrativo_id)
        .where(EtapaCierre.expediente_id.in_(ids))
    )).all()
    cierre_map = {r.expediente_id: r.acto_administrativo_id for r in cierre_rows}

    concepto_rows = (await db.execute(
        select(
            EtapaAcogerConcepto.id,
            EtapaAcogerConcepto.expediente_id,
            EtapaAcogerConcepto.tipo_acogida_concepto,
            EtapaAcogerConcepto.acto_administrativo_id,
        ).where(EtapaAcogerConcepto.expediente_id.in_(ids))
    )).all()
    concepto_map = {r.expediente_id: r for r in concepto_rows}

    informe_rows = (await db.execute(
        select(
            InformeTecnico.expediente_id,
            InformeTecnico.tipo_informe,
            InformeTecnico.fecha_programacion_visita,
            InformeTecnico.fecha_aceptacion_informe,
        ).where(InformeTecnico.expediente_id.in_(ids))
    )).all()
    visita_map = {}
    seguimiento_map = {}
    for r in informe_rows:
        if r.tipo_informe == "VISITA":
            visita_map[r.expediente_id] = r
        elif r.tipo_informe == "SEGUIMIENTO":
            seguimiento_map[r.expediente_id] = r

    actos_a_revisar = {aid for aid in cierre_map.values() if aid}
    actos_a_revisar |= {
        r.acto_administrativo_id
        for r in concepto_rows
        if r.tipo_acogida_concepto == "AUTO_REQUERIMIENTO" and r.acto_administrativo_id
    }

    notificados_actos: set = set()
    if actos_a_revisar:
        notif_rows = (await db.execute(
            select(Notificacion.acto_administrativo_id)
            .where(
                Notificacion.acto_administrativo_id.in_(actos_a_revisar),
                Notificacion.notificacion_exitosa == True,
            )
            .distinct()
        )).scalars().all()
        notificados_actos = set(notif_rows)

    concepto_ids = [r.id for r in concepto_rows]
    solicitud_concepto_ids: set = set()
    if concepto_ids:
        sol_rows = (await db.execute(
            select(SolicitudInformacion.etapa_acoger_concepto_id)
            .where(SolicitudInformacion.etapa_acoger_concepto_id.in_(concepto_ids))
        )).scalars().all()
        solicitud_concepto_ids = set(sol_rows)

    involucrados_con: set = set()
    inv_rows = (await db.execute(
        select(ExpedienteInvolucrado.expediente_id)
        .where(ExpedienteInvolucrado.expediente_id.in_(ids))
        .distinct()
    )).scalars().all()
    involucrados_con = set(inv_rows)

    resultado: dict[int, Optional[str]] = {}
    for exp_id in ids:
        resultado[exp_id] = _evaluar_uno(
            archivado=archivado_map.get(exp_id, False),
            cierre_acto_id=cierre_map.get(exp_id),
            concepto=concepto_map.get(exp_id),
            visita=visita_map.get(exp_id),
            seguimiento=seguimiento_map.get(exp_id),
            notificados_actos=notificados_actos,
            solicitud_concepto_ids=solicitud_concepto_ids,
            tiene_involucrados=exp_id in involucrados_con,
        )
    return resultado


async def calcular_estado_uno(db: AsyncSession, expediente_id: int, archivado: bool) -> Optional[str]:
    resultado = await calcular_estados(db, [expediente_id], {expediente_id: archivado})
    return resultado.get(expediente_id)
