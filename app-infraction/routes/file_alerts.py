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
    agrupar_alertas,
    calcular_alertas_activas,
    calcular_alertas_expediente,
    fecha_limite_habiles,
    hoy_bogota,
)
from satc_shared.alertas import LIMITE_MAXIMO, marcar_responsable, paginar_alertas, permisos_de_roles
import services.etapas as etapas_mod

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

async def permisos_del_usuario(user_id: int, alertas) -> set[str]:
    """Permisos del usuario entre los que piden las alertas por rol (solo
    se consultan esos). Pasa por ``services.etapas`` para que los tests
    sustituyan ``verify_permission`` en un solo sitio."""
    return {p for p in permisos_de_roles(alertas) if await etapas_mod.verify_permission(user_id, p)}


def estadisticas_semaforo(alertas) -> dict:
    estadisticas = {"verde": 0, "amarillo": 0, "rojo": 0, "vencido": 0}
    for a in alertas:
        estadisticas[a["semaforo"]["estado"]] += 1
    return estadisticas


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
    """Alertas de la pestaña Alertas (exige ``infraccion_alertas``, el permiso
    que desbloquea la pestaña; con él se ven las dos vistas).

    - ``alcance=mios`` (por defecto, "Mis alertas"): las alertas de las que el
      usuario es responsable AHORA: como persona (``encargado_id``: abogado,
      técnico o líder técnico asignado) o por rol (``roles_responsables``:
      asignar informes, líder de proyecto). Pueden ser de cualquier
      expediente; si no tiene nada asignado, la lista sale vacía.
    - ``alcance=todos`` ("Todas"): todas las alertas.

    Cada alerta trae ``es_responsable`` (``satc_shared.alertas.marcar_responsable``).
    Los expedientes archivados no tienen alertas.

    Sin ``page`` responde como siempre (``alertas[radicado][clave]``; los
    filtros se ignoran). Con ``page`` responde una página de la lista plana
    ordenada por urgencia y % de avance, filtrada por ``radicado``/``estado``/
    ``tipo``: ``alertas`` (cada ítem + ``radicado`` y ``clave``), ``total``,
    ``total_pages``, ``tipos_disponibles`` y ``estadisticas_semaforo`` (del
    alcance completo, sin filtros).
    """
    user_id = verify_gateway_token(request)["user_id"]
    await exigir_permiso(user_id, Permission.FILE_ALERTS)

    radicados, por_expediente = await calcular_alertas_activas(db, hoy_bogota())
    permisos = await permisos_del_usuario(
        user_id, [a for alertas in por_expediente.values() for a in alertas.values()]
    )

    alertas_totales = agrupar_alertas(radicados, por_expediente, user_id, permisos, alcance == "mios")

    base = {
        "ok": True,
        "alcance": alcance,
        # "Todas": expedientes activos; "Mis alertas": los que tienen alguna mía.
        "total_expedientes": len(radicados) if alcance == "todos" else len(alertas_totales),
        "expedientes_con_alertas": len(alertas_totales),
        "estadisticas_semaforo": estadisticas_semaforo(
            a for alertas in alertas_totales.values() for a in alertas.values()
        ),
    }
    if page is not None:
        pagina = paginar_alertas(alertas_totales, page=page, limit=limit,
                                 radicado=radicado, estado=estado, tipo=tipo)
        return JSONResponse(content={**base, **pagina}, status_code=200)
    return JSONResponse(content={**base, "alertas": alertas_totales}, status_code=200)


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

    fecha_hoy = hoy_bogota()
    alertas = await calcular_alertas_expediente(expediente_id, db, fecha_hoy)
    permisos = await permisos_del_usuario(user_id, alertas.values())
    for a in alertas.values():
        marcar_responsable(a, user_id, permisos)
    estadisticas = estadisticas_semaforo(alertas.values())

    return JSONResponse(content={
        "ok": True,
        "radicado": radicado,
        "alertas": alertas,
        "total_alertas": len(alertas),
        "estadisticas_semaforo": estadisticas,
    }, status_code=200)

