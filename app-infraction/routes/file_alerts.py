from fastapi import Request, APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Literal, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
import logging
import os
import pytz

from db.deps import get_db_managed
from db.models.expediente import Expediente
from services.alertas import (
    calcular_alertas_expediente,
    calcular_alertas_expedientes,
    fecha_limite_habiles,
)
from satc_shared.alertas import LIMITE_MAXIMO, paginar_alertas

from core.permission import Permission
ASSIGN_PERMISSION = Permission.ASSIGN_PERMISSION
FILE_MANAGE = Permission.FILE_MANAGE
LOG_PERMISSION = Permission.LOG_PERMISSION

router = APIRouter()
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXP_DAYS = os.getenv("JWT_EXP_DAYS")

bogota_tz = pytz.timezone("America/Bogota")
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = BASE_DIR / "uploads" / "expedientes"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


from utils.verify_token import verify_gateway_token
from services.etapas import exigir_lectura_expediente, exigir_permiso


# ── HELPERS ALERTAS ───────────────────────────────────────────────────────────
# El cálculo vive en services/alertas.py (carga en bloque). Se reexportan los
# nombres de antes para quien los importe desde aquí.
_fecha_limite_habiles = fecha_limite_habiles
_calcular_alertas_expediente_infraccion = calcular_alertas_expediente


# ── ALERTAS DE INFRACCIONES ────────────────────────────────────────────────────

@router.get("/alertas/todas")
async def obtener_alertas_todos_expedientes_infraccion(
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

    - ``alcance=mios`` (por defecto): los expedientes a cargo del usuario
      (comportamiento previo, sin cambios).
    - ``alcance=todos``: todos los expedientes; exige ``infraccion_alertas``.

    Cada alerta trae ``es_responsable`` (el usuario es el abogado responsable
    de ese expediente) para que el frontend enlace a Gestionar o a Consultar.

    Sin ``page`` responde como siempre (``alertas[radicado][clave]``; los
    filtros se ignoran). Con ``page`` responde una página de la lista plana
    ordenada por urgencia y % de avance, filtrada por ``radicado``/``estado``/
    ``tipo``: ``alertas`` (cada ítem + ``radicado`` y ``clave``), ``total``,
    ``total_pages``, ``tipos_disponibles`` y ``estadisticas_semaforo`` (del
    alcance completo, sin filtros).
    """
    user_id = verify_gateway_token(request)["user_id"]

    stmt = select(Expediente.id, Expediente.radicado, Expediente.abogado_responsable_id).order_by(Expediente.id)
    if alcance == "todos":
        await exigir_permiso(user_id, Permission.FILE_ALERTS)
    else:
        stmt = stmt.where(Expediente.abogado_responsable_id == user_id)
    expedientes = (await db.execute(stmt)).all()

    fecha_hoy = date.today()
    alertas_totales = {}
    estadisticas = {"verde": 0, "amarillo": 0, "rojo": 0, "vencido": 0}

    if expedientes:
        por_expediente = await calcular_alertas_expedientes([e[0] for e in expedientes], db, fecha_hoy)
        for exp_id, radicado_exp, abogado_id in expedientes:
            alertas = por_expediente.get(exp_id)
            if alertas:
                es_responsable = abogado_id == user_id
                for a in alertas.values():
                    a["es_responsable"] = es_responsable
                    estadisticas[a["semaforo"]["estado"]] += 1
                alertas_totales[radicado_exp] = alertas

    base = {
        "ok": True,
        "alcance": alcance,
        "total_expedientes": len(expedientes),
        "expedientes_con_alertas": len(alertas_totales),
        "estadisticas_semaforo": estadisticas,
    }
    if page is not None:
        pagina = paginar_alertas(alertas_totales, page=page, limit=limit,
                                 radicado=radicado, estado=estado, tipo=tipo)
        return JSONResponse(content={**base, **pagina}, status_code=200)

    if not expedientes:
        return JSONResponse(content={
            "ok": True, "alcance": alcance, "alertas": {}, "total_expedientes": 0,
            "expedientes_con_alertas": 0,
            "estadisticas_semaforo": {"verde": 0, "amarillo": 0, "rojo": 0, "vencido": 0},
        }, status_code=200)

    return JSONResponse(content={
        "ok": True,
        "alcance": alcance,
        "alertas": alertas_totales,
        "total_expedientes": len(expedientes),
        "expedientes_con_alertas": len(alertas_totales),
        "estadisticas_semaforo": estadisticas,
    }, status_code=200)


@router.get("/alertas/{expediente_id}")
async def obtener_alertas_expediente_infraccion(
    request: Request,
    expediente_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    user_id = verify_gateway_token(request)["user_id"]
    # Misma regla que el resto de lecturas del expediente: consultar ve
    # cualquiera; gestionar, solo los que tiene a cargo (403 si no).
    row = await exigir_lectura_expediente(db, expediente_id, user_id)
    radicado = row.radicado

    fecha_hoy = date.today()
    alertas = await calcular_alertas_expediente(expediente_id, db, fecha_hoy)

    estadisticas = {"verde": 0, "amarillo": 0, "rojo": 0, "vencido": 0}
    for a in alertas.values():
        estadisticas[a["semaforo"]["estado"]] += 1

    return JSONResponse(content={
        "ok": True,
        "radicado": radicado,
        "alertas": alertas,
        "total_alertas": len(alertas),
        "estadisticas_semaforo": estadisticas,
    }, status_code=200)

