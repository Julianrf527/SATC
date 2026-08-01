from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, insert
from datetime import datetime
from pydantic import BaseModel
from zoneinfo import ZoneInfo
import logging
import asyncio
import json

#----- DB -----
from db.deps import get_db_managed
from db.models.notificacion import Notificacion

router = APIRouter()

class NotificacionRequest(BaseModel):
    mensaje: str
    id_vinculada: str
    tipo: str
    usuario_id: int

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from utils.insertLog import insert_auditoria
from utils.verify_token import verify_gateway_token, verify_service_token

# ---------- ENDPOINTS ----------

@router.post("/add")
async def crear_notificacion(
    request: Request,
    data: NotificacionRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """Crea una notificación para un usuario. Solo service-to-service."""
    verify_service_token(request)

    if not data.mensaje.strip():
        raise HTTPException(
            status_code=400,
            detail="El mensaje no puede estar vacío"
        )

    if not data.id_vinculada.strip():
        raise HTTPException(
            status_code=400,
            detail="El id_vinculada no puede estar vacío"
        )

    if not data.tipo.strip():
        raise HTTPException(
            status_code=400,
            detail="El tipo no puede estar vacío"
        )

    # Una entidad vinculada tiene a lo sumo una notificación viva por usuario:
    # se borra la anterior antes de insertar la nueva.
    stmt = delete(Notificacion).where(
        Notificacion.id_vinculada == data.id_vinculada,
        Notificacion.usuario_id == data.usuario_id
    )
    await db.execute(stmt)
    await db.commit()

    stmt = insert(Notificacion).values(
        mensaje=data.mensaje.strip(),
        id_vinculada=data.id_vinculada.strip(),
        tipo=data.tipo.strip(),
        usuario_id=data.usuario_id,
        fecha_creacion=datetime.now(ZoneInfo("America/Bogota"))
    )

    await db.execute(stmt)
    await db.commit()

    logger.info(f"Notificación creada exitosamente para usuario {data.usuario_id}: {data.mensaje[:50]}...")

    return JSONResponse(
        content={
            "ok": True,
            "message": "Notificación creada exitosamente"
        },
        status_code=201
    )

@router.delete("/delete-all")
async def borrar_todas_notificaciones_usuario(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    """Elimina todas las notificaciones del usuario ("marcar todas como leídas")."""
    token_data = verify_gateway_token(request)
    user_id = token_data["user_id"]

    query = select(Notificacion).where(Notificacion.usuario_id == user_id)
    res = await db.execute(query)
    notificaciones = res.scalars().all()

    if not notificaciones:
        return JSONResponse(
            content={
                "ok": True,
                "msg": "No hay notificaciones para eliminar",
                "count": 0
            },
            status_code=200
        )

    count = len(notificaciones)
    ids_eliminados = []

    for notificacion in notificaciones:
        datos_anteriores = {
            "id": notificacion.id,
            "usuario_id": notificacion.usuario_id,
            "mensaje": notificacion.mensaje,
            "id_vinculada": notificacion.id_vinculada,
            "tipo": notificacion.tipo,
            "fecha_creacion": notificacion.fecha_creacion.isoformat() if notificacion.fecha_creacion else None
        }

        await insert_auditoria(
            db=db,
            usuario_id=token_data["user_id"],
            tipo_evento="ELIMINACION_NOTIFICACION",
            resultado="EXITOSO",
            detalle=f"Eliminación masiva - Marcar todas como leídas",
            datos_anteriores=datos_anteriores
        )
        ids_eliminados.append(notificacion.id)

    stmr = delete(Notificacion).where(Notificacion.usuario_id == token_data["user_id"])
    await db.execute(stmr)
    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "msg": f"{count} notificación(es) eliminada(s) exitosamente",
            "count": count,
            "ids_eliminados": ids_eliminados
        },
        status_code=200
    )

@router.delete("/linked/{linked_id}")
async def borrar_notificacion_por_vinculada(
    request: Request,
    linked_id: str,
    db: AsyncSession = Depends(get_db_managed),
):
    """Elimina las notificaciones asociadas a un id_vinculada (entidad cerrada o borrada)."""
    token_data = verify_gateway_token(request)

    query = select(Notificacion).where(Notificacion.id_vinculada == linked_id)
    res = await db.execute(query)
    notificaciones = res.scalars().all()

    if not notificaciones:
        raise HTTPException(status_code=404, detail="No se encontraron notificaciones con ese ID vinculado")

    ids_eliminados = []
    for notificacion in notificaciones:
        datos_anteriores = {
            "id": notificacion.id,
            "usuario_id": notificacion.usuario_id,
            "mensaje": notificacion.mensaje,
            "id_vinculada": notificacion.id_vinculada,
            "tipo": notificacion.tipo,
            "fecha_creacion": notificacion.fecha_creacion.isoformat() if notificacion.fecha_creacion else None
        }

        await insert_auditoria(
            db=db,
            usuario_id=token_data["user_id"],
            tipo_evento="ELIMINACION_NOTIFICACION",
            resultado="EXITOSO",
            detalle=f"Eliminación masiva de notificación vinculada a '{linked_id}'",
            datos_anteriores=datos_anteriores
        )
        ids_eliminados.append(notificacion.id)

    stmr = delete(Notificacion).where(Notificacion.id_vinculada == linked_id)
    result = await db.execute(stmr)
    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "msg": f"{result.rowcount} notificación(es) eliminada(s) exitosamente",
            "ids_eliminados": ids_eliminados
        },
        status_code=200
    )

@router.delete("/{noti_id}")
async def borrar_notificacion(
    request: Request,
    noti_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)

    # id + usuario_id en el mismo WHERE: una notificación ajena da el mismo 404
    # que una inexistente, así no se pueden enumerar IDs de otros usuarios.
    query = select(Notificacion).where(
        Notificacion.id == noti_id,
        Notificacion.usuario_id == token_data["user_id"],
    )
    res = await db.execute(query)
    notificacion = res.scalar_one_or_none()

    if notificacion is None:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")

    datos_anteriores = {
        "id": notificacion.id,
        "usuario_id": notificacion.usuario_id,
        "mensaje": notificacion.mensaje,
        "id_vinculada": notificacion.id_vinculada,
        "tipo": notificacion.tipo,
        "fecha_creacion": notificacion.fecha_creacion.isoformat() if notificacion.fecha_creacion else None
    }

    stmr = delete(Notificacion).where(Notificacion.id == noti_id)
    await db.execute(stmr)

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
        tipo_evento="ELIMINACION_NOTIFICACION",
        resultado="EXITOSO",
        detalle=f"Eliminación de notificación tipo '{notificacion.tipo}' (ID: {noti_id})",
        datos_anteriores=datos_anteriores
    )

    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse(content={"ok": True, "msg": "Notificación eliminada exitosamente"}, status_code=200)

@router.get("/stream")
async def stream_notificaciones(
    request: Request,
):
    """Stream SSE de notificaciones (actualización cada 30s).

    No usa get_db_managed: abre una sesión nueva por consulta dentro del
    generador, porque una sesión de request no sobrevive a una conexión de
    larga vida.
    """
    user_id = None
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"]

        async def event_generator():
            from db.database import SessionLocal

            try:
                logger.info(f"Iniciando stream SSE para usuario {user_id}")

                while True:
                    if await request.is_disconnected():
                        logger.info(f"Cliente {user_id} desconectado del stream SSE")
                        break

                    async with SessionLocal() as db:
                        stmt = select(
                            Notificacion.id,
                            Notificacion.mensaje,
                            Notificacion.id_vinculada,
                            Notificacion.tipo,
                        ).where(
                            Notificacion.usuario_id == user_id
                        ).order_by(
                            Notificacion.fecha_creacion.desc()
                        )

                        result = await db.execute(stmt)
                        notificaciones = result.all()

                        notificaciones_list = [
                            {
                                "id": n.id,
                                "mensaje": n.mensaje,
                                "id_vinculada": n.id_vinculada,
                                "tipo": n.tipo,
                            }
                            for n in notificaciones
                        ]

                    data = json.dumps({"notifications": notificaciones_list})
                    yield f"data: {data}\n\n"

                    # El intervalo de 30s se parte en 3 para intercalar heartbeats
                    # (líneas ':' en SSE) y detectar desconexiones sin esperar todo el ciclo.
                    for _ in range(3):
                        await asyncio.sleep(10)

                        if await request.is_disconnected():
                            logger.info(f"Cliente {user_id} desconectado durante heartbeat")
                            return

                        yield ": heartbeat\n\n"

            except asyncio.CancelledError:
                logger.info(f"Stream SSE cancelado para usuario {user_id}")
            except Exception as e:
                logger.error(f"Error en stream SSE para usuario {user_id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                yield f"data: {json.dumps({'error': 'Error interno del servidor'})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Para nginx
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error al iniciar stream SSE para usuario {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")
