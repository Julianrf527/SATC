from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dotenv import load_dotenv
from typing import List, Dict, Optional
import logging
import httpx
import os

from db.models.expediente import Expediente
from db.models.expediente_involucrado import ExpedienteInvolucrado

load_dotenv()

gateway_url = os.getenv("GATEWAY_URL", "http://localhost:8000")
logger = logging.getLogger(__name__)


async def get_involucrado_by_id(db: AsyncSession, involucrado_id: int) -> Dict:
    """
    Obtiene los datos de un involucrado dado su ID (desde app-involved a través del API Gateway).
    
    Args:
        db: Sesión de base de datos (no usada, mantenida por compatibilidad)
        involucrado_id: ID del involucrado a buscar
    
    Returns:
        Dict con los datos del involucrado o solo el ID si hay error
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/involveds/bulk",
                json={"ids": [involucrado_id]},
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
    Obtiene múltiples involucrados por sus IDs usando el bulk endpoint.
    
    Args:
        db: Sesión de base de datos (no usada, mantenida por compatibilidad)
        involucrados_ids: Lista de IDs de involucrados
    
    Returns:
        Lista de involucrados con sus datos completos
    """
    if not involucrados_ids:
        return []
    
    try:
        payload = {"ids": involucrados_ids}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/involveds/bulk",
                json=payload,
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


async def get_involved_by_expedientes_ids(
    db: AsyncSession, 
    expediente_id: List[int]
) -> defaultdict:
    """
    Obtiene los involucrados agrupados por expediente usando el bulk endpoint.
    Optimizado para cargar múltiples expedientes de una sola vez.
    
    Args:
        db: Sesión de base de datos
        expediente_id: Lista de IDs de expedientes
    
    Returns:
        defaultdict donde la clave es el expediente_id y el valor es la lista de involucrados
    """
    involucrados_map = defaultdict(list)
    
    if not expediente_id:
        return involucrados_map

    # 1. Obtener relaciones expediente-involucrado
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

    # 2. Obtener IDs únicos de involucrados
    involucrados_ids = list(set(r.involucrado_id for r in relaciones))
    
    # 3. Llamar al bulk endpoint para obtener todos los involucrados
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{gateway_url}/involveds/bulk",
                json={"ids": involucrados_ids},
                timeout=10.0
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    data_involved = result.get("data", [])
                    
                    # 4. Crear mapa de involucrados por ID para acceso rápido
                    inv_data_map = {inv["id"]: inv for inv in data_involved}

                    # 5. Agrupar involucrados por expediente
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
