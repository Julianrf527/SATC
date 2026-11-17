from dotenv import load_dotenv
import logging
import traceback

from satc_shared.clients import UsersClient

load_dotenv()
logger = logging.getLogger(__name__)

# Notificaciones en app-users, directo (east-west) con x-service-token de docs-service.
users_client = UsersClient.from_env("docs-service")


async def create_notification(
    mensaje: str,
    id_vinculada: str,
    tipo: str,
    usuario_id: int
) -> dict:
    """
    Crea una notificación para un usuario en app-users.

    Nunca lanza: los fallos se devuelven como {'ok': False, ...} para que un
    problema de notificación no aborte la operación que la disparó.
    """
    try:
        logger.info(f"Datos notificación: tipo={tipo}, usuario_id={usuario_id}, mensaje={mensaje[:50]}...")
        await users_client.create_notification(
            mensaje=mensaje, id_vinculada=id_vinculada, tipo=tipo, usuario_id=usuario_id
        )
        logger.info(f"Notificación creada para usuario {usuario_id}: {mensaje}")
        return {"ok": True, "message": "Notificación creada"}
    except Exception as e:
        logger.error(f"Error llamando al servicio de notificaciones: {e}")
        return {"ok": False, "message": str(e)}

# Todas las notificaciones de app-docs son del módulo Documentos: el frontend
# enruta por tipo "documento" (los flujos de otras apps notifican por su cuenta).
TIPO_NOTIFICACION = "documento"


async def notify_assignment(
    documento_id: int,
    documento_nombre: str,
    revisor_id: int,
    version_actual: int,
) -> dict:
    """Notifica a un revisor que ha sido asignado a un documento."""
    try:
        mensaje = f"Asignado para revisión (v{version_actual})\n{documento_nombre}"
        resultado = await create_notification(
            mensaje=mensaje,
            id_vinculada=str(documento_id),
            tipo=TIPO_NOTIFICACION,
            usuario_id=revisor_id
        )
        logger.info(f"Resultado notify_assignment documento={documento_id} revisor={revisor_id}: {resultado}")
        return resultado
    except Exception as e:
        logger.error(f"ERROR en notify_assignment: {e}")
        logger.error(traceback.format_exc())
        return {"ok": False, "message": str(e)}


async def notify_new_version(
    documento_id: int,
    documento_nombre: str,
    version_numero: int,
    revisores_ids: list[int],
) -> list[dict]:
    """Notifica a todos los revisores que se subió una nueva versión."""
    mensaje = f"Nueva versión (v{version_numero})\n{documento_nombre}"
    return [
        await create_notification(
            mensaje=mensaje,
            id_vinculada=str(documento_id),
            tipo=TIPO_NOTIFICACION,
            usuario_id=revisor_id
        )
        for revisor_id in revisores_ids
    ]


async def notify_document_rejected(
    documento_id: int,
    documento_nombre: str,
    creador_id: int,
    numero_devoluciones: int,
    max_devoluciones: int = 3,
    con_adjunto: bool = False,
) -> dict:
    """Notifica al creador que su documento fue devuelto."""
    detalle = ", con documento de observaciones" if con_adjunto else ""
    mensaje = f"Documento devuelto ({numero_devoluciones}/{max_devoluciones}){detalle}\n{documento_nombre}"
    return await create_notification(
        mensaje=mensaje,
        id_vinculada=str(documento_id),
        tipo=TIPO_NOTIFICACION,
        usuario_id=creador_id
    )


async def notify_document_approved(
    documento_id: int,
    documento_nombre: str,
    creador_id: int,
) -> dict:
    """Notifica al creador que su documento fue aprobado."""
    mensaje = f"Documento aprobado\n{documento_nombre}"
    return await create_notification(
        mensaje=mensaje,
        id_vinculada=str(documento_id),
        tipo=TIPO_NOTIFICACION,
        usuario_id=creador_id
    )


async def notify_document_finalized(
    documento_id: int,
    documento_nombre: str,
    creador_id: int,
    max_devoluciones: int = 3,
) -> dict:
    """Notifica al creador que su documento fue finalizado al llegar al máximo de devoluciones."""
    mensaje = f"Finalizado tras {max_devoluciones} devoluciones\n{documento_nombre}"
    return await create_notification(
        mensaje=mensaje,
        id_vinculada=str(documento_id),
        tipo=TIPO_NOTIFICACION,
        usuario_id=creador_id
    )
