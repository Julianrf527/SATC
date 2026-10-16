from fastapi import Request, APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Literal, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date

from db.deps import get_db_managed
from db.models.expediente import Expediente

from utils.verify_token import verify_gateway_token
from services.alertas import calcular_alertas_expediente, calcular_alertas_expedientes
from satc_shared.alertas import LIMITE_MAXIMO, paginar_alertas
from services.permisos import exigir_alguno, exigir_lectura_expediente
from core.permission import Permission

router = APIRouter()


@router.get("/alerts/all")
async def obtener_alertas_todos_expedientes(
    request: Request,
    alcance: Literal["mios", "todos"] = Query("mios"),
    page: Optional[int] = Query(None, ge=1, description="Si llega, respuesta paginada (lista plana)."),
    limit: int = Query(10, ge=1, le=LIMITE_MAXIMO),
    radicado: Optional[str] = Query(None, description="Coincidencia parcial, sin mayúsculas."),
    estado: Optional[Literal["verde", "amarillo", "rojo", "vencido"]] = Query(None),
    tipo: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_managed),
):
    """Alertas de la pestaña Alertas.

    - ``alcance=mios`` (por defecto): los expedientes asignados al usuario
      (comportamiento previo, sin cambios).
    - ``alcance=todos``: todos los expedientes; exige ``sancionatorio_alertas``.

    Cada alerta trae ``es_responsable`` (el usuario es el encargado de ese
    expediente) para que el frontend enlace a Gestionar o a Consultar.

    Sin ``page`` responde como siempre (``alertas[radicado][clave]``; los
    filtros se ignoran). Con ``page`` responde una página de la lista plana
    ordenada por urgencia y % de avance, filtrada por ``radicado``/``estado``/
    ``tipo``: ``alertas`` (cada ítem + ``radicado`` y ``clave``), ``total``,
    ``total_pages``, ``tipos_disponibles`` y ``estadisticas_semaforo`` (del
    alcance completo, sin filtros).
    """
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    stmt = select(Expediente.id, Expediente.radicado, Expediente.encargado_id).order_by(Expediente.id)
    if alcance == "todos":
        await exigir_alguno(user_id, Permission.FILE_ALERTS)
    else:
        stmt = stmt.where(Expediente.encargado_id == user_id)
    result = await db.execute(stmt)
    expedientes = result.all()

    if not expedientes and page is None:
        return JSONResponse(
            content={
                "ok": True,
                "alcance": alcance,
                "alertas": {},
                "total_expedientes": 0,
                "expedientes_con_alertas": 0
            },
            status_code=200
        )

    alertas_totales = {}
    fecha_hoy = date.today()

    por_expediente = await calcular_alertas_expedientes([e.id for e in expedientes], db, fecha_hoy)
    for exp_id, radicado_exp, encargado_id in expedientes:
        alertas = por_expediente.get(exp_id)
        if alertas:
            es_responsable = encargado_id == user_id
            for alerta in alertas.values():
                alerta["es_responsable"] = es_responsable
            alertas_totales[radicado_exp] = alertas

    estadisticas = {
        "verde": 0,
        "amarillo": 0,
        "rojo": 0,
        "vencido": 0
    }

    for alertas_expediente in alertas_totales.values():
        for alerta in alertas_expediente.values():
            estado_alerta = alerta["semaforo"]["estado"]
            estadisticas[estado_alerta] += 1

    if page is not None:
        pagina = paginar_alertas(alertas_totales, page=page, limit=limit,
                                 radicado=radicado, estado=estado, tipo=tipo)
        return JSONResponse(
            content={
                "ok": True,
                "alcance": alcance,
                "total_expedientes": len(expedientes),
                "expedientes_con_alertas": len(alertas_totales),
                "estadisticas_semaforo": estadisticas,
                **pagina,
            },
            status_code=200
        )

    return JSONResponse(
        content={
            "ok": True,
            "alcance": alcance,
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
    # Misma regla que el resto de lecturas del expediente: consultar ve
    # cualquiera; gestionar, solo los que tiene a cargo (403 si no).
    row = await exigir_lectura_expediente(db, expediente_id, user_id)
    radicado = row.radicado

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
