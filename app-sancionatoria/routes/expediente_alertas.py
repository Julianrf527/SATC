from fastapi import Request, APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date

from db.deps import get_db_managed
from db.models.expediente import Expediente

from utils.verify_token import verify_gateway_token
from services.alertas import calcular_alertas_expediente

router = APIRouter()


@router.get("/alerts/all")
async def obtener_alertas_todos_expedientes(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    """Obtiene todas las alertas de todos los expedientes asignados al usuario autenticado."""
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    stmt = select(Expediente.radicado).where(Expediente.encargado_id == user_id)
    result = await db.execute(stmt)
    expedientes = result.scalars().all()

    if not expedientes:
        return JSONResponse(
            content={
                "ok": True,
                "alertas": {},
                "total_expedientes": 0,
                "expedientes_con_alertas": 0
            },
            status_code=200
        )

    alertas_totales = {}
    fecha_hoy = date.today()

    for radicado in expedientes:
        alertas = await calcular_alertas_expediente(radicado, db, fecha_hoy)
        if alertas:
            alertas_totales[radicado] = alertas

    estadisticas = {
        "verde": 0,
        "amarillo": 0,
        "rojo": 0,
        "vencido": 0
    }

    for radicado, alertas_expediente in alertas_totales.items():
        for alerta in alertas_expediente.values():
            estado = alerta["semaforo"]["estado"]
            estadisticas[estado] += 1

    return JSONResponse(
        content={
            "ok": True,
            "alertas": alertas_totales,
            "total_expedientes": len(expedientes),
            "expedientes_con_alertas": len(alertas_totales),
            "estadisticas_semaforo": estadisticas
        },
        status_code=200
    )

@router.get("/alerts/{expediente_id}")
async def obtener_alertas_expediente(
    expediente_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    """Obtiene todas las alertas de un expediente específico."""
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    stmt = select(Expediente.radicado).where(
        Expediente.id == expediente_id,
        Expediente.encargado_id == user_id
    )
    result = await db.execute(stmt)
    radicado = result.scalar_one_or_none()

    if not radicado:
        raise HTTPException(
            status_code=404,
            detail=f"Expediente con ID {expediente_id} no encontrado o no tiene acceso"
        )

    fecha_hoy = date.today()
    alertas = await calcular_alertas_expediente(radicado, db, fecha_hoy)

    estadisticas = {
        "verde": 0,
        "amarillo": 0,
        "rojo": 0,
        "vencido": 0
    }

    for alerta in alertas.values():
        estado = alerta["semaforo"]["estado"]
        estadisticas[estado] += 1

    return JSONResponse(
        content={
            "ok": True,
            "radicado": radicado,
            "alertas": alertas,
            "total_alertas": len(alertas),
            "estadisticas_semaforo": estadisticas
        },
        status_code=200
    )
