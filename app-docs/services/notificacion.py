import os
import httpx
from dotenv import load_dotenv
import logging
import traceback

load_dotenv()

logger = logging.getLogger(__name__)

# URL del Gateway para comunicación entre servicios
GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://api-gateway:8000")

# Log de configuración
logger.info(f"Servicio de notificaciones configurado con GATEWAY_URL: {GATEWAY_URL}")

async def crear_notificacion_usuario(
    mensaje: str,
    id_vinculada: str,
    tipo: str,
    usuario_id: int
) -> dict:
    """
    Crea una notificación para un usuario.
    
    Args:
        mensaje: Texto de la notificación
        id_vinculada: ID del documento/entidad relacionada
        tipo: Tipo de notificación ('documento', 'expediente', etc.)
        usuario_id: ID del usuario que recibirá la notificación
    
    Returns:
        dict con 'ok' (bool) y 'message' (str)
    """
    try:
        endpoint_url = f"{GATEWAY_URL}/users/notification/add"
        logger.info(f"Intentando crear notificación en: {endpoint_url}")
        logger.info(f"Datos: tipo={tipo}, usuario_id={usuario_id}, mensaje={mensaje[:50]}...")
        
        # Headers con token del gateway para autenticación entre servicios
        secret_gateway = os.getenv("SECRET_GATEWAY")
        headers = {
            "X-Gateway-Token": secret_gateway,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                endpoint_url,
                json={
                    "mensaje": mensaje,
                    "id_vinculada": id_vinculada,
                    "tipo": tipo,
                    "usuario_id": usuario_id
                },
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Notificación creada para usuario {usuario_id}: {mensaje}")
                return {"ok": True, "message": "Notificación creada"}
            else:
                logger.warning(
                    f"Error al crear notificación: {response.status_code} - {response.text}"
                )
                return {"ok": False, "message": "Error al crear notificación"}
    
    except Exception as e:
        logger.error(f"Error llamando al servicio de notificaciones: {e}")
        return {"ok": False, "message": str(e)}


async def notificar_asignacion_revisor(
    documento_id: int,
    documento_nombre: str,
    revisor_id: int,
    version_actual: int
) -> dict:
    """Notifica a un revisor que ha sido asignado a un documento."""
    try:
        logger.info(f"=== INICIANDO notificar_asignacion_revisor ===")
        logger.info(f"documento_id={documento_id}, revisor_id={revisor_id}")
        
        mensaje = f"Te han asignado como revisor del documento '{documento_nombre}' (versión {version_actual})"
        resultado = await crear_notificacion_usuario(
            mensaje=mensaje,
            id_vinculada=str(documento_id),
            tipo="documento",
            usuario_id=revisor_id
        )
        logger.info(f"Resultado notificar_asignacion_revisor: {resultado}")
        return resultado
    except Exception as e:
        logger.error(f"ERROR en notificar_asignacion_revisor: {e}")
        logger.error(traceback.format_exc())
        return {"ok": False, "message": str(e)}


async def notificar_nueva_version(
    documento_id: int,
    documento_nombre: str,
    version_numero: int,
    revisores_ids: list[int]
) -> list[dict]:
    """Notifica a todos los revisores que se subió una nueva versión."""
    resultados = []
    mensaje = f"Se ha subido una nueva versión ({version_numero}) del documento '{documento_nombre}'"
    
    for revisor_id in revisores_ids:
        resultado = await crear_notificacion_usuario(
            mensaje=mensaje,
            id_vinculada=str(documento_id),
            tipo="documento",
            usuario_id=revisor_id
        )
        resultados.append(resultado)
    
    return resultados


async def notificar_documento_rechazado(
    documento_id: int,
    documento_nombre: str,
    creador_id: int,
    numero_devoluciones: int
) -> dict:
    """Notifica al creador que su documento fue rechazado."""
    mensaje = f"Tu documento '{documento_nombre}' ha sido devuelto. Devolución {numero_devoluciones}/3"
    return await crear_notificacion_usuario(
        mensaje=mensaje,
        id_vinculada=str(documento_id),
        tipo="documento",
        usuario_id=creador_id
    )


async def notificar_documento_aprobado(
    documento_id: int,
    documento_nombre: str,
    creador_id: int
) -> dict:
    """Notifica al creador que su documento fue aprobado."""
    mensaje = f"¡Felicidades! Tu documento '{documento_nombre}' ha sido aprobado"
    return await crear_notificacion_usuario(
        mensaje=mensaje,
        id_vinculada=str(documento_id),
        tipo="documento",
        usuario_id=creador_id
    )


async def notificar_documento_finalizado(
    documento_id: int,
    documento_nombre: str,
    creador_id: int
) -> dict:
    """Notifica al creador que su documento fue finalizado tras 3 rechazos."""
    mensaje = f"Tu documento '{documento_nombre}' ha sido finalizado tras alcanzar 3 devoluciones"
    return await crear_notificacion_usuario(
        mensaje=mensaje,
        id_vinculada=str(documento_id),
        tipo="documento",
        usuario_id=creador_id
    )