from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv
from typing import List, Dict
import logging
import httpx
import os

from db.models.expediente import Expediente
from db.models.expediente_involucrado import ExpedienteInvolucrado
load_dotenv()

_raw_involved_url = (
    os.getenv("INVOLVED_SERVICE_URL")
    or os.getenv("INVOLVED_ROUTE")
    or "http://app-involved:8004"
).rstrip("/")
involved_service_url = (
    _raw_involved_url
    if _raw_involved_url.endswith("/involved")
    else f"{_raw_involved_url}/involved"
)
service_secret = os.getenv("SERVICE_SECRET_KEY")

from utils.generate_service_jwt import generate_service_jwt

logger = logging.getLogger(__name__)


async def get_involucrado_by_id(db: AsyncSession, involucrado_id: int) -> Dict:
    """
    Datos de un involucrado desde app-involved. Ante cualquier fallo devuelve
    solo {"id": involucrado_id} en vez de propagar el error: los listados que
    lo usan deben renderizar igual aunque app-involved esté caído.

    `db` no se usa; se mantiene por compatibilidad con los llamadores.
    """
    try:
        async with httpx.AsyncClient() as client:
            if not service_secret:
                raise RuntimeError("SERVICE_SECRET_KEY no configurado, no se puede autenticar contra app-involved")
            headers = {
                "x-service-token": generate_service_jwt("sanctioning-service", service_secret),
            }
            response = await client.post(
                f"{involved_service_url}/bulk",
                json={"ids": [involucrado_id]},
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok") and result.get("data"):
                    return result["data"][0]
                else:
                    logger.warning(f"No data for involucrado {involucrado_id}")
                    return {"id": involucrado_id}
            else:
                logger.error(
                    f"Error fetching involucrado {involucrado_id}: "
                    f"{response.status_code} - {response.text}"
                )
                return {"id": involucrado_id}
                
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching involucrado {involucrado_id}")
        return {"id": involucrado_id}
    except Exception as e:
        logger.error(f"Exception fetching involucrado {involucrado_id}: {e}")
        return {"id": involucrado_id}

async def get_involucrados_by_ids(
    db: AsyncSession, 
    involucrados_ids: List[int],
) -> List[Dict]:
    """
    Múltiples involucrados por sus IDs vía el bulk endpoint de app-involved.

    `db` no se usa; se mantiene por compatibilidad con los llamadores.
    """
    if not involucrados_ids:
        return []
    
    try:
        payload = {"ids": involucrados_ids}
        
        async with httpx.AsyncClient() as client:
            if not service_secret:
                raise RuntimeError("SERVICE_SECRET_KEY no configurado, no se puede autenticar contra app-involved")
            headers = {
                "x-service-token": generate_service_jwt("sanctioning-service", service_secret),
            }
            response = await client.post(
                f"{involved_service_url}/bulk",
                json=payload,
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    return result.get("data", [])
                else:
                    logger.warning(f"Bulk request not ok for IDs {involucrados_ids}")
                    return []
            else:
                logger.error(
                    f"Error in bulk request for IDs {involucrados_ids}: "
                    f"{response.status_code} - {response.text}"
                )
                return []
                
    except httpx.TimeoutException:
        logger.error(f"Timeout in bulk request for IDs {involucrados_ids}")
        return []
    except Exception as e:
        logger.error(f"Exception in bulk request: {e}")
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
    res_rel = await db.execute(st_rel)
    relaciones = res_rel.all()

    if not relaciones:
        return involucrados_map

    involucrados_ids = list(set(r.involucrado_id for r in relaciones))
    
    try:
        async with httpx.AsyncClient() as client:
            if not service_secret:
                raise RuntimeError("SERVICE_SECRET_KEY no configurado, no se puede autenticar contra app-involved")
            headers = {
                "x-service-token": generate_service_jwt("sanctioning-service", service_secret),
            }
            response = await client.post(
                f"{involved_service_url}/bulk",
                json={"ids": involucrados_ids},
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    data_involved = result.get("data", [])

                    inv_data_map = {inv["id"]: inv for inv in data_involved}

                    for exp_id, inv_id in relaciones:
                        if inv_id in inv_data_map:
                            involucrados_map[exp_id].append(inv_data_map[inv_id])
                else:
                    logger.warning(
                        f"Bulk request not ok for expedientes {expediente_id}"
                    )
            else:
                logger.error(
                    f"Error fetching involucrados for expedientes {expediente_id}: "
                    f"{response.status_code} - {response.text}"
                )
                
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching involucrados for expedientes {expediente_id}")
    except Exception as e:
        logger.error(f"Exception fetching involucrados: {e}")

    return involucrados_map
