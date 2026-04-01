import httpx
import logging
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models.expediente import Expediente
from db.models.expediente_involucrado import ExpedienteInvolucrado

logger = logging.getLogger(__name__)

async def get_involucrados_por_radicados(db: AsyncSession, radicados: list[str], gateway_url: str) -> defaultdict:
    """
    Obtiene los datos de los involucrados (desde app-involved a través del API Gateway)
    dada una lista de radicados de expediente.
    """
    involucrados_map = defaultdict(list)
    if not radicados:
        return involucrados_map

    st_rel = (
        select(
            Expediente.radicado,
            ExpedienteInvolucrado.involucrado_id
        )
        .join(ExpedienteInvolucrado, Expediente.id == ExpedienteInvolucrado.expediente_id)
        .where(Expediente.radicado.in_(radicados))
    )
    res_rel = await db.execute(st_rel)
    relaciones = res_rel.all()

    if relaciones:
        involucrados_ids = list(set(r.involucrado_id for r in relaciones))
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{gateway_url}/involved/bulk",
                    json={"ids": involucrados_ids},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data_involved = response.json().get("data", [])
                    inv_data_map = {inv["id"]: inv for inv in data_involved}

                    for rad, inv_id in relaciones:
                        if inv_id in inv_data_map:
                            inv = inv_data_map[inv_id]
                            involucrados_map[rad].append(inv)
        except Exception as e:
            logger.error(f"Error fetching involucrados for radicados {radicados}: {e}")

    return involucrados_map
