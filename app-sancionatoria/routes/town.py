from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging

from db.deps import get_db_managed
from db.models.municipio import Municipio
from db.models.vereda import Vereda
from utils.functions import calcular_dias_laborales
from utils.verify_token import verify_gateway_token

router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class BusinessDaysRequest(BaseModel):
    fecha_inicio: str
    fecha_fin: str

@router.get("/rural-district")
async def cargar_municipios_y_veredas(
    request: Request,
    db: AsyncSession = Depends(get_db_managed)
):
    verify_gateway_token(request)

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
                "nombre": row["m_name"],
                "veredas": [],
            }
        if row["v_id"] is not None:
            towns[m_id]["veredas"].append(
                {"id": row["v_id"], "nombre": row["v_name"]}
            )

    data = list(towns.values())

    if data:
        logger.info(f"Municipios cargados correctamente: {len(data)} encontrados.")
    else:
        logger.warning("Se ejecutó /towns-sidewalk pero no se encontraron registros.")

    return JSONResponse(
        content={"ok": True, "data": data},
        status_code=200,
        media_type="application/json; charset=utf-8",
        headers={"Content-Type": "application/json; charset=utf-8"}
    )

@router.get("/rural-district/{municipio_id}")
async def obtener_veredas_por_municipio(
    request: Request,
    municipio_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    verify_gateway_token(request)

    stmt = select(Vereda).where(Vereda.municipio_id == municipio_id)
    result = await db.execute(stmt)
    veredas = result.scalars().all()

    veredas_data = [{"id": ve.id, "nombre": ve.nombre} for ve in veredas]

    return JSONResponse(
        content={"ok": True, "veredas": veredas_data},
        status_code=200
    )
    
@router.post("/utils/business-days")
async def calcular_dias_laborales_endpoint(
    request: BusinessDaysRequest
):
    from datetime import datetime
    fecha_inicio = datetime.strptime(request.fecha_inicio.split(' ')[0], "%Y-%m-%d").date()
    fecha_fin = datetime.strptime(request.fecha_fin.split(' ')[0], "%Y-%m-%d").date()
    
    dias = calcular_dias_laborales(fecha_inicio, fecha_fin)
    return {"dias_laborales": dias}