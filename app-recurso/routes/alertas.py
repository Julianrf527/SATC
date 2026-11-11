"""Alertas de vencimiento (prefijo ``/alertas``). Reglas en ``services/alertas.py``.

- ``GET /alertas/todas``: pestaña Alertas (``recurso_gestionar``).
  ``alcance=mios`` → alertas cuyo encargado es el usuario; ``alcance=todos`` →
  todas. Mismo contrato que infraction (``satc_shared.alertas``); cada alerta
  trae ``es_responsable`` y ``expediente_id``.
- ``GET /alertas/aviso-visita``: aviso (no bloquea) de la fecha de visita
  técnica frente al numerado del auto que admite, para el modal de cargue.
- ``GET /alertas/{expediente_id}``: alertas de un expediente (lectura).
"""
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_gestion, requiere_lectura
from db.deps import get_db_managed
from db.models.expediente import Expediente
from satc_shared.alertas import LIMITE_MAXIMO, paginar_alertas
from services.alertas import (
    PLAZO_VISITA,
    advertencia_visita,
    calcular_alertas,
    estadisticas,
    hoy_bogota,
    limite_visita,
)

router = APIRouter()


@router.get("/todas")
async def alertas_todas(
    request: Request,
    alcance: Literal["mios", "todos"] = Query("mios"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=LIMITE_MAXIMO),
    radicado: Optional[str] = Query(None, description="Coincidencia parcial, sin mayúsculas."),
    estado: Optional[Literal["verde", "amarillo", "rojo", "vencido"]] = Query(None),
    tipo: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_managed),
):
    usuario = await requiere_gestion(request)
    por_expediente = await calcular_alertas(db, hoy_bogota())

    radicados = {}
    if por_expediente:
        radicados = dict((await db.execute(
            select(Expediente.id, Expediente.radicado).where(Expediente.id.in_(list(por_expediente)))
        )).all())

    alertas_por_radicado: dict[str, dict] = {}
    for exp_id, alertas in por_expediente.items():
        for a in alertas.values():
            a["es_responsable"] = a["encargado_id"] == usuario.user_id
        if alcance == "mios":
            alertas = {k: a for k, a in alertas.items() if a["es_responsable"]}
        if alertas:
            alertas_por_radicado[radicados.get(exp_id, str(exp_id))] = alertas

    if alcance == "todos":
        total_expedientes = await db.scalar(select(func.count()).select_from(Expediente))
    else:
        total_expedientes = len(alertas_por_radicado)

    base = {
        "ok": True,
        "alcance": alcance,
        "total_expedientes": total_expedientes or 0,
        "expedientes_con_alertas": len(alertas_por_radicado),
        "estadisticas_semaforo": estadisticas(a for al in alertas_por_radicado.values() for a in al.values()),
    }
    pagina = paginar_alertas(alertas_por_radicado, page=page, limit=limit, radicado=radicado, estado=estado, tipo=tipo)
    return {**base, **pagina}


@router.get("/aviso-visita")
async def aviso_visita(
    request: Request,
    fecha_numerado: date = Query(..., description="Fecha de numerado del auto que admite"),
    fecha_visita: Optional[date] = Query(None, description="Fecha de visita técnica"),
):
    """Fecha límite de la visita (numerado + 10 hábiles) y el aviso, si aplica.
    Solo informa: el cargue no se bloquea."""
    await requiere_gestion(request)
    return {
        "ok": True,
        "data": {
            "fecha_limite": limite_visita(fecha_numerado).isoformat(),
            "dias_habiles": PLAZO_VISITA,
            "advertencia": advertencia_visita(fecha_numerado, fecha_visita),
        },
    }


@router.get("/{expediente_id}")
async def alertas_expediente(request: Request, expediente_id: int, db: AsyncSession = Depends(get_db_managed)):
    usuario = await requiere_lectura(request)
    radicado = await db.scalar(select(Expediente.radicado).where(Expediente.id == expediente_id))
    if radicado is None:
        raise HTTPException(status_code=404, detail="Expediente no encontrado")
    alertas = (await calcular_alertas(db, hoy_bogota(), expediente_id)).get(expediente_id, {})
    for a in alertas.values():
        a["es_responsable"] = a["encargado_id"] == usuario.user_id
    return {
        "ok": True,
        "radicado": radicado,
        "alertas": alertas,
        "total_alertas": len(alertas),
        "estadisticas_semaforo": estadisticas(alertas.values()),
    }
