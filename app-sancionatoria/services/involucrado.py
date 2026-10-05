from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv
from typing import List, Dict
import logging

from satc_shared.clients import InvolvedClient

from db.models.expediente import Expediente
from db.models.expediente_involucrado import ExpedienteInvolucrado

load_dotenv()

logger = logging.getLogger(__name__)

# Directo a app-involved (INVOLVED_SERVICE_URL, o el legado INVOLVED_ROUTE;
# el sufijo /involved se normaliza) con x-service-token de sanctioning-service.
involved_client = InvolvedClient.from_env("sanctioning-service")


async def get_involucrado_by_id(db: AsyncSession, involucrado_id: int) -> Dict:
    """
    Datos de un involucrado desde app-involved. Ante cualquier fallo devuelve
    solo {"id": involucrado_id} en vez de propagar el error: los listados que
    lo usan deben renderizar igual aunque app-involved esté caído.

    `db` no se usa; se mantiene por compatibilidad con los llamadores.
    """
    try:
        data = await involved_client.bulk([involucrado_id])
    except Exception as e:
        logger.error(f"Error fetching involucrado {involucrado_id}: {e}")
        return {"id": involucrado_id}
    if not data:
        logger.warning(f"No data for involucrado {involucrado_id}")
        return {"id": involucrado_id}
    return data[0]


async def get_involucrados_by_ids(
    db: AsyncSession,
    involucrados_ids: List[int],
) -> List[Dict]:
    """
    Múltiples involucrados por sus IDs vía el bulk endpoint de app-involved.
    Ante fallo devuelve [].

    `db` no se usa; se mantiene por compatibilidad con los llamadores.
    """
    if not involucrados_ids:
        return []
    try:
        return await involved_client.bulk(involucrados_ids)
    except Exception as e:
        logger.error(f"Error in bulk request for IDs {involucrados_ids}: {e}")
        return []


async def get_involucrados_by_expedientes_ids(
    db: AsyncSession,
    expediente_id: List[int]
) -> defaultdict:
    """
    Involucrados agrupados por expediente ({expediente_id: [involucrado, ...]}),
    resolviendo todos los IDs en una sola llamada bulk a app-involved.
    """
    involucrados_map = defaultdict(list)

    if not expediente_id:
        return involucrados_map

    st_rel = (
        select(
            Expediente.id,
            ExpedienteInvolucrado.involucrado_id
        )
        .join(ExpedienteInvolucrado, Expediente.id == ExpedienteInvolucrado.expediente_id)
        .where(Expediente.id.in_(expediente_id))
    )
    relaciones = (await db.execute(st_rel)).all()

    if not relaciones:
        return involucrados_map

    involucrados_ids = list(set(r.involucrado_id for r in relaciones))

    try:
        data_involved = await involved_client.bulk(involucrados_ids)
    except Exception as e:
        logger.error(f"Error fetching involucrados for expedientes {expediente_id}: {e}")
        return involucrados_map

    inv_data_map = {inv["id"]: inv for inv in data_involved}
    for exp_id, inv_id in relaciones:
        if inv_id in inv_data_map:
            involucrados_map[exp_id].append(inv_data_map[inv_id])

    return involucrados_map
