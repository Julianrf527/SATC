"""
Helpers compartidos de actos administrativos y etapas, usados por los routers
de acto (acto_admin / acto_notificacion / acto_comunicacion).

Resuelven el contexto (expediente + radicado + encargado) a partir de una etapa
o de un acto administrativo, siguiendo las FK reales del dominio (el acto no
tiene FK directa a expediente: se llega vía etapa_concepto / etapa_cierre /
medida_preventiva).
"""
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.expediente import Expediente
from db.models.acto_administrativo import ActoAdministrativo
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.medida_preventiva import MedidaPreventiva
from db.models.etapa_respuesta import EtapaRespuesta


def resolve_etapa_ids(
    etapa_concepto_id: Optional[int],
    etapa_cierre_id: Optional[int],
    etapa_id: Optional[int],
):
    if etapa_concepto_id is None and etapa_cierre_id is None and etapa_id is not None:
        etapa_concepto_id = etapa_id

    if etapa_concepto_id and etapa_cierre_id:
        raise HTTPException(
            status_code=422,
            detail="Debe enviar solo etapa_concepto_id o etapa_cierre_id",
        )

    if not etapa_concepto_id and not etapa_cierre_id:
        raise HTTPException(
            status_code=422,
            detail="Debe enviar etapa_concepto_id o etapa_cierre_id",
        )

    return etapa_concepto_id, etapa_cierre_id


async def get_etapa_context(
    db: AsyncSession,
    etapa_concepto_id: Optional[int],
    etapa_cierre_id: Optional[int],
):
    if etapa_concepto_id:
        stmt = (
            select(
                EtapaAcogerConcepto,
                Expediente.id,
                Expediente.radicado,
                Expediente.abogado_responsable_id,
            )
            .join(Expediente, Expediente.id == EtapaAcogerConcepto.expediente_id)
            .where(EtapaAcogerConcepto.id == etapa_concepto_id)
        )
        row = (await db.execute(stmt)).first()
        if not row:
            raise HTTPException(status_code=404, detail="Etapa concepto no encontrada")
        etapa, expediente_id, radicado, encargado_id = row
        return "concepto", etapa, expediente_id, radicado, encargado_id

    stmt = (
        select(
            EtapaCierre,
            Expediente.id,
            Expediente.radicado,
            Expediente.abogado_responsable_id,
        )
        .join(Expediente, Expediente.id == EtapaCierre.expediente_id)
        .where(EtapaCierre.id == etapa_cierre_id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Etapa cierre no encontrada")
    etapa, expediente_id, radicado, encargado_id = row
    return "cierre", etapa, expediente_id, radicado, encargado_id


async def get_acto_context(db: AsyncSession, acto_admin_id: int):
    stmt_concepto = (
        select(
            ActoAdministrativo,
            EtapaAcogerConcepto,
            Expediente.id,
            Expediente.radicado,
            Expediente.abogado_responsable_id,
        )
        .join(EtapaAcogerConcepto, EtapaAcogerConcepto.acto_administrativo_id == ActoAdministrativo.id)
        .join(Expediente, Expediente.id == EtapaAcogerConcepto.expediente_id)
        .where(ActoAdministrativo.id == acto_admin_id)
    )
    row = (await db.execute(stmt_concepto)).first()
    if row:
        acto, etapa, expediente_id, radicado, encargado_id = row
        return "concepto", acto, etapa, expediente_id, radicado, encargado_id

    stmt_cierre = (
        select(
            ActoAdministrativo,
            EtapaCierre,
            Expediente.id,
            Expediente.radicado,
            Expediente.abogado_responsable_id,
        )
        .join(EtapaCierre, EtapaCierre.acto_administrativo_id == ActoAdministrativo.id)
        .join(Expediente, Expediente.id == EtapaCierre.expediente_id)
        .where(ActoAdministrativo.id == acto_admin_id)
    )
    row = (await db.execute(stmt_cierre)).first()
    if row:
        acto, etapa, expediente_id, radicado, encargado_id = row
        return "cierre", acto, etapa, expediente_id, radicado, encargado_id

    stmt_medida = (
        select(
            ActoAdministrativo,
            MedidaPreventiva,
            Expediente.id,
            Expediente.radicado,
            Expediente.abogado_responsable_id,
        )
        .join(MedidaPreventiva, MedidaPreventiva.acto_administrativo_id == ActoAdministrativo.id)
        .join(EtapaRespuesta, EtapaRespuesta.id == MedidaPreventiva.etapa_respuesta_id)
        .join(Expediente, Expediente.id == EtapaRespuesta.expediente_id)
        .where(ActoAdministrativo.id == acto_admin_id)
    )
    row = (await db.execute(stmt_medida)).first()
    if row:
        acto, medida, expediente_id, radicado, encargado_id = row
        return "medida", acto, medida, expediente_id, radicado, encargado_id

    raise HTTPException(status_code=404, detail="Acto administrativo no encontrado")
