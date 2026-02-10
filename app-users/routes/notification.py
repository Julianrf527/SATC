from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, insert
from datetime import datetime
from pydantic import BaseModel
from zoneinfo import ZoneInfo
import logging

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
from utils.verify_gateway_token import verify_gateway_token, verify_service_token

# ---------- ENDPOINTS ----------

@router.get("/all/{id_user}")
async def cargar_notificaciones(
    request: Request,
    id_user: int,
    db: AsyncSession = Depends(get_db),
):  
    try:
        user_id = verify_gateway_token(request)
        if id_user != user_id:
            raise HTTPException(status_code=401, detail="No cuenta con los permisos")
        
        stmr = select(
            Notificacion.id,
            Notificacion.mensaje,
            Notificacion.id_vinculada,
            Notificacion.tipo
        ).where(Notificacion.usuario_id == id_user)
        
        result = await db.execute(stmr)
        result = result.all()

        data = [
            {
                "id": noti[0], 
                "mensaje": noti[1], 
                "id_vinculada": noti[2],
                "tipo": noti[3]
            }
            for noti in result
        ]

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)
    
    except Exception as e:
        logger.error(f"Error al obtener notificaciones para el usuario ID: {id_user} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error en el servidor.")

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

@router.delete("/{id_noti}")
async def borrar_notificacion(
    request: Request,
    id_noti: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)
        
        # Obtener la notificación completa antes de eliminarla
        query = select(Notificacion).where(Notificacion.id == id_noti)
        res = await db.execute(query)
        notificacion = res.scalar_one_or_none()

        if notificacion is None:
            raise HTTPException(status_code=404, detail="Notificación no encontrada")
        
        if notificacion.usuario_id != user_id:
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
        stmr = delete(Notificacion).where(Notificacion.id == id_noti)
        await db.execute(stmr)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tabla_afectada="notificacion",
            tipo_operacion="DELETE",
            descripcion=f"Eliminación de notificación tipo '{notificacion.tipo}' (ID: {id_noti})",
            id_registro=str(id_noti),
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
        logger.exception(f"Error al eliminar notificación con ID {id_noti}: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")

@router.delete("/linked/{id_linked}")
async def borrar_notificacion_por_vinculada(
    request: Request,
    id_linked: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Elimina todas las notificaciones asociadas a un id_vinculada específico.
    Útil cuando se elimina o finaliza una entidad relacionada.
    """
    try:
        user_id = verify_gateway_token(request)
        
        # Obtener todas las notificaciones con ese id_vinculada
        query = select(Notificacion).where(Notificacion.id_vinculada == id_linked)
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
                usuario_id=user_id,
                tabla_afectada="notificacion",
                tipo_operacion="DELETE",
                descripcion=f"Eliminación masiva de notificación vinculada a '{id_linked}'",
                id_registro=str(notificacion.id),
                datos_anteriores=datos_anteriores
            )
            ids_eliminados.append(notificacion.id)

        # Eliminar todas las notificaciones con ese id_vinculada
        stmr = delete(Notificacion).where(Notificacion.id_vinculada == id_linked)
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
        logger.exception(f"Error al eliminar notificaciones con id_vinculada {id_linked}: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")
    
@router.delete("/user/{user_id}")
async def borrar_todas_notificaciones_usuario(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Elimina todas las notificaciones de un usuario específico.
    Útil para la función "Marcar todas como leídas".
    """
    try:
        authenticated_user_id = verify_gateway_token(request)
        
        # Verificar que el usuario solo pueda eliminar sus propias notificaciones
        if authenticated_user_id != user_id:
            raise HTTPException(
                status_code=403, 
                detail="No tienes permisos para eliminar notificaciones de otro usuario"
            )
        
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
                usuario_id=authenticated_user_id,
                tabla_afectada="notificacion",
                tipo_operacion="DELETE",
                descripcion=f"Eliminación masiva - Marcar todas como leídas",
                id_registro=str(notificacion.id),
                datos_anteriores=datos_anteriores
            )
            ids_eliminados.append(notificacion.id)

        # Eliminar todas las notificaciones del usuario
        stmr = delete(Notificacion).where(Notificacion.usuario_id == user_id)
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