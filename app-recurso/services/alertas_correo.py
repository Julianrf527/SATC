"""Correo semanal de alertas (lunes 8:00, America/Bogota).

Cada usuario recibe su "Mis alertas": las alertas de las que es responsable
según ``satc_shared.alertas.es_responsable`` (encargado o, si el documento
está en revisión, uno de los roles del paso actual). Sin alertas no hay correo.

Gunicorn corre varios workers y cada uno tiene su scheduler: todos disparan
el job a la misma hora. El primero que inserta la semana en
``envio_alertas_semanal`` envía; los demás (y un reinicio posterior dentro del
margen) no.
"""
from __future__ import annotations

import asyncio
import copy
import logging
from datetime import date, timedelta
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.permission import Permission
from db.models.envio_alertas_semanal import EnvioAlertasSemanal
from db.models.expediente import Expediente
from satc_shared.alertas import es_responsable
import services.users as users_svc
from services.alertas import calcular_alertas, estadisticas, hoy_bogota

logger = logging.getLogger(__name__)

TITULO = "Reporte Semanal de Alertas - Concesiones de Aguas"
JOB_ID = "envio_alertas_semanal_recurso"

# Permisos con los que un usuario puede ser responsable de una alerta.
PERMISOS_DESTINATARIOS: tuple[str, ...] = (Permission.MANAGE, Permission.TECNICO, *Permission.REVISORES)


async def destinatarios() -> dict[int, dict]:
    """``{user_id: {nombre, correo, permisos}}`` de quienes pueden ser
    responsables (una consulta por permiso, no por usuario)."""
    listas = await asyncio.gather(*(users_svc.get_users_by_permission(p) for p in PERMISOS_DESTINATARIOS))
    usuarios: dict[int, dict] = {}
    for permiso, por_usuario in zip(PERMISOS_DESTINATARIOS, listas):
        for uid, datos in por_usuario.items():
            u = usuarios.setdefault(uid, {"nombre": datos.get("nombre"), "correo": datos.get("correo"),
                                          "permisos": set()})
            u["permisos"].add(permiso)
    return usuarios


def reporte_de(user_id: int, permisos: set[str], por_radicado: dict[str, dict[str, dict]]) -> Optional[dict]:
    """"Mis alertas" del usuario en el formato del correo; None si no tiene."""
    propias: dict[str, dict[str, dict]] = {}
    for radicado, alertas in por_radicado.items():
        mias = {clave: copy.deepcopy(a) for clave, a in alertas.items() if es_responsable(a, user_id, permisos)}
        for a in mias.values():
            a["es_responsable"] = True
        if mias:
            propias[radicado] = mias
    if not propias:
        return None
    return {
        "alertas": propias,
        "total_expedientes": len(propias),
        "expedientes_con_alertas": len(propias),
        "estadisticas_semaforo": estadisticas(a for al in propias.values() for a in al.values()),
    }


async def enviar_reportes(db: AsyncSession, hoy: Optional[date] = None) -> dict[str, int]:
    """Calcula las alertas una vez y envía a cada destinatario las suyas."""
    resumen = {"enviados": 0, "sin_alertas": 0, "sin_correo": 0, "errores": 0}
    por_expediente = await calcular_alertas(db, hoy or hoy_bogota())
    if not por_expediente:
        logger.info("Reporte semanal de alertas: no hay alertas")
        return resumen
    radicados = dict((await db.execute(
        select(Expediente.id, Expediente.radicado).where(Expediente.id.in_(list(por_expediente)))
    )).all())
    por_radicado = {radicados.get(exp_id, str(exp_id)): alertas for exp_id, alertas in por_expediente.items()}

    for uid, u in (await destinatarios()).items():
        reporte = reporte_de(uid, u["permisos"], por_radicado)
        if reporte is None:
            resumen["sin_alertas"] += 1
            continue
        if not u["correo"]:
            logger.warning("Reporte semanal de alertas: el usuario %s no tiene correo", uid)
            resumen["sin_correo"] += 1
            continue
        try:
            await users_svc.users_client.send_alert_report([u["correo"]], reporte, title=TITULO)
            resumen["enviados"] += 1
        except Exception as e:  # un correo fallido no detiene a los demás
            logger.error("Reporte semanal de alertas: falló el envío al usuario %s: %s", uid, e)
            resumen["errores"] += 1
    logger.info("Reporte semanal de alertas de recurso: %s", resumen)
    return resumen


def lunes_de(dia: date) -> date:
    return dia - timedelta(days=dia.weekday())


async def reclamar_envio(db: AsyncSession, semana: date) -> bool:
    """True si este proceso queda a cargo del envío de ``semana`` (el commit
    hace visible el reclamo de inmediato a los demás workers)."""
    fila = await db.execute(
        pg_insert(EnvioAlertasSemanal).values(semana=semana)
        .on_conflict_do_nothing(index_elements=["semana"])
        .returning(EnvioAlertasSemanal.semana)
    )
    reclamado = fila.scalar_one_or_none() is not None
    await db.commit()
    return reclamado


async def ejecutar_envio_semanal(sesion: Callable[[], AsyncSession], hoy: Optional[date] = None) -> bool:
    """Job del lunes: envía si este worker reclama la semana. Devuelve si envió."""
    hoy = hoy or hoy_bogota()
    async with sesion() as db:
        semana = lunes_de(hoy)
        if not await reclamar_envio(db, semana):
            logger.info("Reporte semanal de alertas %s ya enviado por otro proceso", semana)
            return False
        await enviar_reportes(db, hoy)
        return True


def crear_scheduler(sesion: Callable[[], AsyncSession]) -> AsyncIOScheduler:
    """Scheduler con el envío semanal registrado (sin iniciar).

    El job debe ser una función ``async``: APScheduler solo espera las
    corrutinas si la función registrada es corrutina (con una ``lambda`` que
    devuelve una corrutina, esta se crea y nunca se ejecuta).
    """
    async def job_envio_semanal() -> None:
        try:
            await ejecutar_envio_semanal(sesion)
        except Exception as e:
            logger.error("Reporte semanal de alertas: error en el job: %s", e, exc_info=True)

    scheduler = AsyncIOScheduler(timezone="America/Bogota")
    scheduler.add_job(
        job_envio_semanal,
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0, timezone="America/Bogota"),
        id=JOB_ID,
        name="Envío semanal de alertas - Concesiones",
        replace_existing=True,
        # Si el servicio estaba caído a las 8:00, se envía al volver (hasta
        # 12 h después); varias ejecuciones atrasadas cuentan como una.
        misfire_grace_time=12 * 3600,
        coalesce=True,
        max_instances=1,
    )
    return scheduler

