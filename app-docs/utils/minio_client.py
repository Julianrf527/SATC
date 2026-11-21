"""
Utilidades para manejo de MinIO - Almacenamiento de objetos
"""
import asyncio
import os
import io
from minio import Minio
from minio.error import S3Error
from datetime import timedelta, datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from dotenv import load_dotenv
import logging
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

load_dotenv()
logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_SECURE = os.getenv("MINIO_SECURE", "false").lower() == "true"
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "satc-expedientes")

# SSE-S3 apagado por defecto: este MinIO no tiene KMS configurado.
MINIO_SSE_ENABLED = os.getenv("MINIO_SSE_ENABLED", "false").lower() == "true"

minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

def init_minio():
    """
    Inicializa MinIO creando el bucket si no existe
    """
    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
            logger.info(f"Bucket '{MINIO_BUCKET}' creado exitosamente")
        else:
            logger.info(f"Bucket '{MINIO_BUCKET}' ya existe")
        return True
    except S3Error as e:
        logger.error(f"Error inicializando MinIO: {e}")
        return False


def generate_hash_based_path(file_hash: str, original_filename: str) -> str:
    """
    Ruta de almacenamiento derivada del hash: files/{prefix}/{hash}{ext}
    (ej. files/a3/a3f5c8d9e2b1....pdf).

    El prefijo de 2 caracteres reparte los archivos en ~256 subdirectorios;
    todo en uno solo degrada el listado del bucket.
    """
    extension = Path(original_filename).suffix or ""
    hash_prefix = file_hash[:2]
    object_path = f"files/{hash_prefix}/{file_hash}{extension}"
    
    logger.debug(f"Ruta generada: {object_path} para hash {file_hash[:8]}...")
    return object_path

def upload_file_to_minio(file_data: bytes, object_name: str, content_type: str = "application/octet-stream") -> dict:
    """
    Sube un archivo a MinIO, con encriptación SSE-S3 si está habilitada.
    Devuelve {'ok', 'url', 'message'}.
    """
    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            init_minio()

        file_stream = io.BytesIO(file_data)
        file_size = len(file_data)

        metadata = {}
        if MINIO_SSE_ENABLED:
            metadata["X-Amz-Server-Side-Encryption"] = "AES256"
            logger.debug(f"Encriptación SSE-S3 habilitada para {object_name}")
        
        minio_client.put_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            data=file_stream,
            length=file_size,
            content_type=content_type,
            metadata=metadata
        )
        
        # URL interna (bucket/objeto), no una URL pública servible.
        url = f"{MINIO_BUCKET}/{object_name}"
        
        encryption_status = "encriptado" if MINIO_SSE_ENABLED else "sin encriptar"
        logger.info(f"Archivo subido exitosamente a MinIO ({encryption_status}): {url}")
        return {
            "ok": True,
            "url": url,
            "message": "Archivo subido exitosamente"
        }
    
    except S3Error as e:
        logger.error(f"Error subiendo archivo a MinIO: {e}")
        return {
            "ok": False,
            "url": None,
            "message": f"Error subiendo archivo: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error inesperado subiendo archivo: {e}")
        return {
            "ok": False,
            "url": None,
            "message": f"Error inesperado: {str(e)}"
        }

def delete_file_from_minio(object_name: str) -> dict:
    """
    Elimina un archivo de MinIO. `object_name` puede venir con o sin el
    prefijo del bucket. Devuelve {'ok', 'message'}.
    """
    try:
        # object_name puede venir prefijado con el bucket.
        if object_name.startswith(f"{MINIO_BUCKET}/"):
            object_name = object_name.replace(f"{MINIO_BUCKET}/", "")
        
        minio_client.remove_object(MINIO_BUCKET, object_name)
        
        logger.info(f"Archivo eliminado exitosamente de MinIO: {object_name}")
        return {
            "ok": True,
            "message": "Archivo eliminado exitosamente"
        }
    
    except S3Error as e:
        logger.error(f"Error eliminando archivo de MinIO: {e}")
        return {
            "ok": False,
            "message": f"Error eliminando archivo: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error inesperado eliminando archivo: {e}")
        return {
            "ok": False,
            "message": f"Error inesperado: {str(e)}"
        }

def descargar_a_archivo(object_name: str, ruta: str) -> bool:
    """Descarga un objeto de MinIO directo a disco (sin cargarlo en memoria)."""
    try:
        if object_name.startswith(f"{MINIO_BUCKET}/"):
            object_name = object_name.replace(f"{MINIO_BUCKET}/", "")
        minio_client.fget_object(MINIO_BUCKET, object_name, ruta)
        return True
    except Exception as e:
        logger.error(f"Error descargando {object_name} de MinIO: {e}")
        return False


def get_file_from_minio(object_name: str) -> dict:
    """
    Obtiene un archivo de MinIO. Devuelve {'ok', 'data', 'message'}.
    """
    try:
        if object_name.startswith(f"{MINIO_BUCKET}/"):
            object_name = object_name.replace(f"{MINIO_BUCKET}/", "")
        
        response = minio_client.get_object(MINIO_BUCKET, object_name)
        file_data = response.read()
        response.close()
        response.release_conn()
        
        logger.info(f"Archivo obtenido exitosamente de MinIO: {object_name}")
        return {
            "ok": True,
            "data": file_data,
            "message": "Archivo obtenido exitosamente"
        }
    
    except S3Error as e:
        logger.error(f"Error obteniendo archivo de MinIO: {e}")
        return {
            "ok": False,
            "data": None,
            "message": f"Error obteniendo archivo: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error inesperado obteniendo archivo: {e}")
        return {
            "ok": False,
            "data": None,
            "message": f"Error inesperado: {str(e)}"
        }

def _nombre_objeto(object_name: str) -> str:
    if object_name.startswith(f"{MINIO_BUCKET}/"):
        return object_name[len(MINIO_BUCKET) + 1:]
    return object_name


def tamano_objeto(object_name: str) -> int:
    """Tamaño en bytes del objeto (stat). Lanza S3Error si no existe."""
    return minio_client.stat_object(MINIO_BUCKET, _nombre_objeto(object_name)).size


def abrir_objeto(object_name: str, offset: int = 0, length: int = 0):
    """Abre el objeto para leerlo por bloques (``length=0`` = hasta el final).
    Devuelve la respuesta de urllib3: quien la use debe cerrarla y liberar la
    conexión (``close()`` + ``release_conn()``). Lanza S3Error si no existe."""
    return minio_client.get_object(MINIO_BUCKET, _nombre_objeto(object_name), offset=offset, length=length)


def get_presigned_url(object_name: str, expires: timedelta = timedelta(hours=1)) -> dict:
    """
    URL pre-firmada para acceso temporal directo a un objeto.
    Devuelve {'ok', 'url', 'message'}.
    """
    try:
        # Limpiar el nombre del objeto
        if object_name.startswith(f"{MINIO_BUCKET}/"):
            object_name = object_name.replace(f"{MINIO_BUCKET}/", "")
        
        url = minio_client.presigned_get_object(
            bucket_name=MINIO_BUCKET,
            object_name=object_name,
            expires=expires
        )
        
        logger.info(f"URL pre-firmada generada para: {object_name}")
        return {
            "ok": True,
            "url": url,
            "message": "URL generada exitosamente"
        }
    
    except S3Error as e:
        logger.error(f"Error generando URL pre-firmada: {e}")
        return {
            "ok": False,
            "url": None,
            "message": f"Error generando URL: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error inesperado generando URL: {e}")
        return {
            "ok": False,
            "url": None,
            "message": f"Error inesperado: {str(e)}"
        }

def copy_file_in_minio(source_object: str, dest_object: str) -> dict:
    """
    Copia un objeto dentro del mismo bucket. Devuelve {'ok', 'url', 'message'}.
    """
    try:
        if source_object.startswith(f"{MINIO_BUCKET}/"):
            source_object = source_object.replace(f"{MINIO_BUCKET}/", "")
        if dest_object.startswith(f"{MINIO_BUCKET}/"):
            dest_object = dest_object.replace(f"{MINIO_BUCKET}/", "")
        
        from minio.commonconfig import CopySource
        minio_client.copy_object(
            bucket_name=MINIO_BUCKET,
            object_name=dest_object,
            source=CopySource(MINIO_BUCKET, source_object)
        )
        
        url = f"{MINIO_BUCKET}/{dest_object}"
        
        logger.info(f"Archivo copiado exitosamente: {source_object} -> {dest_object}")
        return {
            "ok": True,
            "url": url,
            "message": "Archivo copiado exitosamente"
        }
    
    except S3Error as e:
        logger.error(f"Error copiando archivo en MinIO: {e}")
        return {
            "ok": False,
            "url": None,
            "message": f"Error copiando archivo: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Error inesperado copiando archivo: {e}")
        return {
            "ok": False,
            "url": None,
            "message": f"Error inesperado: {str(e)}"
        }

async def find_file_by_hash(db: AsyncSession, file_hash: str) -> Optional[dict]:
    """
    Busca un archivo ya almacenado por su hash SHA256, o None si no existe.
    """
    from db.models.file_hash import FileHash

    file_record = await db.scalar(select(FileHash).where(FileHash.file_hash == file_hash))
    if not file_record:
        return None
    return {
        "id": file_record.id,
        "file_hash": file_record.file_hash,
        "file_url": file_record.file_url,
        "content_type": file_record.content_type,
        "file_size": file_record.file_size,
        "numero_usos": file_record.numero_usos,
    }


async def upload_file_with_deduplication(
    db: AsyncSession,
    file_data: bytes,
    original_filename: str,
    content_type: str = "application/octet-stream",
    object_name: str = None
) -> dict:
    """
    Sube un archivo a MinIO con deduplicación por hash SHA256 y lo registra en
    ``file_hash``. Si el hash ya existe reutiliza el objeto; en ambos casos
    marca ``ultima_subida`` (periodo de gracia de la limpieza).

    Hace commit propio a propósito: el objeto ya está en MinIO, así que su fila
    debe quedar aunque la operación que lo usa falle después. Con numero_usos=0
    la limpieza los borra a ambos pasado el periodo de gracia; con un rollback
    quedaría un objeto en MinIO sin fila, que nada limpia. Quien llama no debe
    tener cambios pendientes en la sesión.
    """
    from db.models.file_hash import FileHash
    from utils.hash_utils import calcular_hash_archivo

    try:
        file_hash = calcular_hash_archivo(file_data)
        file_size = len(file_data)
        ahora = datetime.now(ZoneInfo("America/Bogota"))

        # Reutilización. El UPDATE espera si la limpieza tiene la fila bloqueada;
        # si la terminó borrando no afecta filas y el archivo se sube de nuevo.
        existente = (await db.execute(
            update(FileHash)
            .where(FileHash.file_hash == file_hash)
            .values(ultima_subida=ahora)
            .returning(FileHash.id, FileHash.file_url, FileHash.numero_usos)
        )).first()
        if existente is not None:
            await db.commit()
            logger.info(f"Archivo duplicado reutilizado. Hash: {file_hash}, URL: {existente.file_url}")
            return {
                "ok": True,
                "url": existente.file_url,
                "message": "Archivo duplicado - URL reutilizada",
                "deduplicated": True,
                "file_hash": file_hash,
                "id": existente.id,
                "numero_usos": existente.numero_usos,
            }

        if not object_name:
            object_name = generate_hash_based_path(file_hash, original_filename)
        upload_result = await asyncio.to_thread(upload_file_to_minio, file_data, object_name, content_type)
        if not upload_result["ok"]:
            return upload_result

        # Upsert: dos subidas simultáneas del mismo archivo nuevo terminan en la
        # misma fila (la ruta del objeto depende solo del hash) en vez de chocar
        # con la restricción única.
        fila = (await db.execute(
            pg_insert(FileHash)
            .values(
                file_hash=file_hash,
                file_url=upload_result["url"],
                content_type=content_type,
                file_size=file_size,
                numero_usos=0,
                created_at=ahora,
                ultima_subida=ahora,
            )
            .on_conflict_do_update(index_elements=[FileHash.file_hash], set_={"ultima_subida": ahora})
            .returning(FileHash.id, FileHash.file_url, FileHash.numero_usos)
        )).one()
        await db.commit()

        logger.info(f"Archivo nuevo subido y registrado. Hash: {file_hash}, URL: {fila.file_url}")
        return {
            "ok": True,
            "url": fila.file_url,
            "message": "Archivo nuevo subido exitosamente",
            "deduplicated": False,
            "file_hash": file_hash,
            "id": fila.id,
            "numero_usos": fila.numero_usos,
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error en upload con deduplicación: {e}")
        return {
            "ok": False,
            "url": None,
            "message": f"Error: {str(e)}",
            "deduplicated": False
        }
