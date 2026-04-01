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
from db.deps import get_db
from db.models.notificacion import Notificacion

router = APIRouter()

class NotificacionRequest(BaseModel):
    mensaje: str
    id_vinculada: str
    tipo: str
    usuario_id: int

#----------- LOGGER ------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

#----------- FUNCIONES ------------

from utils.insertLog import insert_auditoria
from utils.verify_token import verify_gateway_token, verify_service_token

# ---------- ENDPOINTS ----------

@router.post("/add")
async def crear_notificacion(
    request: Request,
    data: NotificacionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Crea una nueva notificación para un usuario.
    Este endpoint es llamado por otros microservicios (ej: sancionatorio, documentos).
    Requiere X-Gateway-Token para autenticación servicio-a-servicio.
    """
    try:
        # Verificar que la petición viene de un servicio autenticado (no requiere user_id)
        verify_service_token(request)
        
        # Validar que el mensaje no esté vacío
        if not data.mensaje.strip():
            raise HTTPException(
                status_code=400,
                detail="El mensaje no puede estar vacío"
            )
        
        # Validar que el id_vinculada no esté vacío
        if not data.id_vinculada.strip():
            raise HTTPException(
                status_code=400,
                detail="El id_vinculada no puede estar vacío"
            )
        
        # Validar que el tipo no esté vacío
        if not data.tipo.strip():
            raise HTTPException(
                status_code=400,
                detail="El tipo no puede estar vacío"
            )
        
        # Eliminar notificaciones duplicadas con el mismo id_vinculada
        stmt = delete(Notificacion).where(
            Notificacion.id_vinculada == data.id_vinculada,
            Notificacion.usuario_id == data.usuario_id
        )
        await db.execute(stmt)
        await db.commit()

        # Insertar notificación
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
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creando notificación: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error al crear la notificación"
        )

@router.delete("/{noti_id}")
async def borrar_notificacion(
    request: Request,
    noti_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        token_data = verify_gateway_token(request)
        
        # Obtener la notificación completa antes de eliminarla
        query = select(Notificacion).where(Notificacion.id == noti_id)
        res = await db.execute(query)
        notificacion = res.scalar_one_or_none()

        if notificacion is None:
            raise HTTPException(status_code=404, detail="Notificación no encontrada")
        
        if notificacion.usuario_id != token_data["user_id"]:
            raise HTTPException(status_code=401, detail="No cuenta con los permisos")

        # Guardar datos para auditoría antes de eliminar
        datos_anteriores = {
            "id": notificacion.id,
            "usuario_id": notificacion.usuario_id,
            "mensaje": notificacion.mensaje,
            "id_vinculada": notificacion.id_vinculada,
            "tipo": notificacion.tipo,
            "fecha_creacion": notificacion.fecha_creacion.isoformat() if notificacion.fecha_creacion else None
        }

        # Eliminar la notificación
        stmr = delete(Notificacion).where(Notificacion.id == noti_id)
        await db.execute(stmr)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=token_data["user_id"],
            documento_usuario=token_data["documento"],
            nombre_usuario=token_data["nombre"],
            tipo_evento="ELIMINACION_NOTIFICACION",
            resultado="EXITOSO",
            detalle=f"Eliminación de notificación tipo '{notificacion.tipo}' (ID: {noti_id})",
            datos_anteriores=datos_anteriores
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()

        return JSONResponse(content={"ok": True, "msg": "Notificación eliminada exitosamente"}, status_code=200)
        
    except HTTPException:
        raise 
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error al eliminar notificación con ID {noti_id}: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")

@router.delete("/linked/{linked_id}")
async def borrar_notificacion_por_vinculada(
    request: Request,
    linked_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Elimina todas las notificaciones asociadas a un id_vinculada específico.
    Útil cuando se elimina o finaliza una entidad relacionada.
    """
    try:
        token_data = verify_gateway_token(request)
        
        # Obtener todas las notificaciones con ese id_vinculada
        query = select(Notificacion).where(Notificacion.id_vinculada == linked_id)
        res = await db.execute(query)
        notificaciones = res.scalars().all()

        if not notificaciones:
            raise HTTPException(status_code=404, detail="No se encontraron notificaciones con ese ID vinculado")

        # Guardar datos para auditoría
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
                documento_usuario=token_data["documento"],
                nombre_usuario=token_data["nombre"],
                tipo_evento="ELIMINACION_NOTIFICACION",
                resultado="EXITOSO",
                detalle=f"Eliminación masiva de notificación vinculada a '{linked_id}'",
                datos_anteriores=datos_anteriores
            )
            ids_eliminados.append(notificacion.id)

        # Eliminar todas las notificaciones con ese id_vinculada
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
        
    except HTTPException:
        raise 
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error al eliminar notificaciones con id_vinculada {linked_id}: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")
    
@router.delete("/delete-all")
async def borrar_todas_notificaciones_usuario(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Elimina todas las notificaciones de un usuario específico.
    Útil para la función "Marcar todas como leídas".
    """
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"]
        
        # Obtener todas las notificaciones del usuario
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

        # Guardar datos para auditoría
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
                documento_usuario=token_data["documento"],
                nombre_usuario=token_data["nombre"],
                tipo_evento="ELIMINACION_NOTIFICACION",
                resultado="EXITOSO",
                detalle=f"Eliminación masiva - Marcar todas como leídas",
                datos_anteriores=datos_anteriores
            )
            ids_eliminados.append(notificacion.id)

        # Eliminar todas las notificaciones del usuario
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
        
    except HTTPException:
        raise 
    except Exception as e:
        await db.rollback()
        logger.exception(f"Error al eliminar todas las notificaciones del usuario {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")

@router.get("/stream")
async def stream_notificaciones(
    request: Request,
):
    """
    Endpoint SSE (Server-Sent Events) para notificaciones en tiempo real.
    Mantiene una conexión abierta y envía actualizaciones cada 30 segundos.

    """
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"]
        
        async def event_generator():
            from db.database import SessionLocal
            
            try:
                logger.info(f"Iniciando stream SSE para usuario {user_id}")
                
                while True:
                    # Verificar si el cliente cerró la conexión
                    if await request.is_disconnected():
                        logger.info(f"Cliente {user_id} desconectado del stream SSE")
                        break
                    
                    # Crear una nueva sesión para cada consulta
                    async with SessionLocal() as db:
                        # Obtener notificaciones actuales
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
                    
                    # Enviar datos en formato SSE
                    data = json.dumps({"notifications": notificaciones_list})
                    yield f"data: {data}\n\n"
                    
                    # Enviar heartbeat cada 15 segundos para mantener la conexión viva
                    # Dividir el sleep de 30s en 2 partes con heartbeat
                    for _ in range(3):  # 3 x 10s = 30s total
                        await asyncio.sleep(10)
                        
                        # Verificar desconexión antes del heartbeat
                        if await request.is_disconnected():
                            logger.info(f"Cliente {user_id} desconectado durante heartbeat")
                            return
                        
                        # Enviar comentario como heartbeat (los comentarios en SSE empiezan con :)
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
