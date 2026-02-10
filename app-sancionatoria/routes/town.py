from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging
import os

#----- DB -----

from db.deps import get_db
from datetime import date
from db.models.municipio import Municipio
from db.models.vereda import Vereda

router = APIRouter()

# ---------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- MODELOS ----------
class RolCreate(BaseModel):
    name: str
    permission: list[int]

class BusinessDaysRequest(BaseModel):
    fecha_inicio: str
    fecha_fin: str

#----------- FUNCIONES ------------

from utils.funtions import calcular_dias_laborales
from utils.verify_gateway_token import verify_gateway_token

# ---------- ENDPOINTS ----------

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/sidewalk")
async def cargar_municipios_y_veredas(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = verify_gateway_token(request)

        stmt = (
            select(
                Municipio.id.label("m_id"),
                Municipio.nombre.label("m_name"),
                Vereda.id.label("v_id"),
                Vereda.nombre.label("v_name"),
            )
            .join(Vereda, Vereda.municipio_id == Municipio.id, isouter=True)
            .order_by(Municipio.nombre, Vereda.nombre)
        )

        result = await db.execute(stmt)
        rows = result.mappings().all()

        towns = {}
        for row in rows:
            m_id = row["m_id"]
            if m_id not in towns:
                towns[m_id] = {
                    "id": m_id,
                    "name": row["m_name"],
                    "sidewalk": [],
                }
            if row["v_id"] is not None:
                towns[m_id]["sidewalk"].append(
                    {"id": row["v_id"], "name": row["v_name"]}
                )

        data = list(towns.values())

        if data:
            logger.info(f"Municipios cargados correctamente: {len(data)} encontrados.")
        else:
            logger.warning("Se ejecutó /towns-sidewalk pero no se encontraron registros.")

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)

    except Exception as e:
        logger.error(f"Error en /towns-sidewalk: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")

@router.get("/sidewalk/{municipio_id}")
async def obtener_veredas_por_municipio(
    request: Request,
    municipio_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)

        stmt = select(Vereda).where(Vereda.municipio_id == municipio_id)
        result = await db.execute(stmt)
        veredas = result.scalars().all()

        veredas_data = [{"id": ve.id, "nombre": ve.nombre} for ve in veredas]

        return JSONResponse(
            content={"ok": True, "veredas": veredas_data},
            status_code=200
        )

    except Exception as e:
        logger.error(f"Error en /town/sidewalk/{municipio_id}: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")
    
@router.post("/utils/business-days")
async def calcular_dias_laborales_endpoint(
    request: BusinessDaysRequest
):
    from datetime import datetime
    # Convertir strings a objetos date
    fecha_inicio = datetime.strptime(request.fecha_inicio.split(' ')[0], "%Y-%m-%d").date()
    fecha_fin = datetime.strptime(request.fecha_fin.split(' ')[0], "%Y-%m-%d").date()
    
    dias = calcular_dias_laborales(fecha_inicio, fecha_fin)
    return {"dias_laborales": dias}