from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv
from typing import List, Dict
import logging

from satc_shared.clients import InvolvedClient

load_dotenv()

logger = logging.getLogger(__name__)

# Directo a app-involved (INVOLVED_SERVICE_URL, o el legado INVOLVED_ROUTE;
# el sufijo /involved se normaliza) con x-service-token de recurso-service.
involved_client = InvolvedClient.from_env("recurso-service")


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

