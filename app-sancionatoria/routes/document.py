from fastapi import UploadFile, File, APIRouter, Depends, HTTPException, Form, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote
from pypdf import PdfWriter, PdfReader
from io import BytesIO
import logging
import pytz
import os

#----- DB -----
from db.deps import get_db
from db.models.etapa import Etapa
from db.models.documento import Documento
from db.models.expediente import Expediente
from db.models.tipo_etapa import TipoEtapa
from db.models.acto_admin import ActoAdmin
from db.models.notificacion import Notificacion
from db.models.involucrado_notificacion import InvolucradoNotificacion
from db.models.comunicacion import Comunicacion
from db.models.involucrado import Involucrado

router = APIRouter()
bogota_tz = pytz.timezone("America/Bogota")

#----------- LOGGER ------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

#----------- FUNCIONES ------------

from utils.verify_gateway_token import verify_gateway_token
from services.crud_file_operations import insert_log_auditoria
from utils.minio_client import (
    upload_file_to_minio,
    upload_file_with_deduplication,
    delete_file_from_minio,
    get_file_from_minio,
    init_minio,
    MINIO_BUCKET
)
from utils.hash_utils import calcular_hash_uploadfile
from utils.antivirus import escanear_archivo, verificar_clamav_disponible
from utils.file_validator import validate_file_complete

# Inicializar MinIO
init_minio()

# ---------- ENDPOINTS ----------

@router.post("/new")
async def crear_documento(
    request: Request,
    radicado: str = Form(...),
    etapa_id: int = Form(...),
    nombre: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Crea un nuevo documento asociado a una etapa.
    Incluye verificación de duplicados (SHA256) y escaneo antivirus (ClamAV).
    """
    try:
        usuario_id = verify_gateway_token(request)
        
        # Validar que el archivo sea PDF
        if not file.content_type == "application/pdf":
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten archivos PDF"
            )
        
        # Verificar que el expediente existe y que el usuario tiene permisos
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )
        
        # Verificar que la etapa existe
        stmt = select(Etapa).where(Etapa.id == etapa_id)
        etapa = await db.scalar(stmt)
        
        if not etapa:
            raise HTTPException(status_code=404, detail="Etapa no encontrada")
        
        # 1. Calcular hash SHA256
        logger.info(f"Calculando hash para archivo: {file.filename}")
        file_hash, file_data = calcular_hash_uploadfile(file)
        
        # 2. Validación completa de seguridad (Caso 8: 5 capas)
        logger.info(f"Validando seguridad del archivo: {file.filename}")
        max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
        
        try:
            validation_result = await validate_file_complete(
                file_data=file_data,
                filename=file.filename,
                max_size_mb=max_size
            )
            sanitized_filename = validation_result["sanitized_filename"]
            mime_type = validation_result["mime_type"]
            logger.info(f"Validacion exitosa: {validation_result}")
        except HTTPException as e:
            logger.error(f"Validacion de seguridad fallo: {e.detail}")
            raise
        
        # 3. Verificar duplicados
        # Buscar si ya existe un documento con el mismo hash
        stmt_hash = select(Documento).where(
            Documento.etapa_id == etapa_id
        )
        result_docs = await db.execute(stmt_hash)
        documentos_existentes = result_docs.scalars().all()
        
        for doc_existente in documentos_existentes:
            # Si la URL contiene el hash, es duplicado
            if file_hash in doc_existente.url_documento:
                logger.warning(f"Archivo duplicado detectado: {file_hash}")
                raise HTTPException(
                    status_code=409,
                    detail=f"Este archivo ya existe en la etapa (documento: {doc_existente.nombre})"
                )
        
        # 4. Escanear con ClamAV (Capa 4 de seguridad)
        logger.info(f"Escaneando archivo con ClamAV: {file.filename}")
        resultado_escaneo = escanear_archivo(file_data, file.filename)
        
        if not resultado_escaneo["ok"]:
            logger.error(f"Archivo rechazado por antivirus: {resultado_escaneo['mensaje']}")
            raise HTTPException(
                status_code=400,
                detail=f"Archivo rechazado: {resultado_escaneo['mensaje']}"
            )
        
        # 5. Subir a MinIO con deduplicación (usar nombre sanitizado)
        logger.info(f"Subiendo archivo a MinIO con deduplicación")
        resultado_upload = await upload_file_with_deduplication(
            db=db,
            file_data=file_data,
            original_filename=sanitized_filename,  # Usar nombre sanitizado
            content_type=mime_type  # Usar MIME detectado
        )
        
        if not resultado_upload["ok"]:
            raise HTTPException(
                status_code=500,
                detail=f"Error subiendo archivo: {resultado_upload.get('message', 'Error desconocido')}"
            )
        
        # 5. Guardar en BD
        url_documento = resultado_upload["url"]
        
        if resultado_upload.get("deduplicated"):
            logger.info(f"Archivo duplicado - Documento - URL reutilizada: {url_documento}")
        else:
            logger.info(f"Archivo nuevo - Documento: {url_documento}")
        
        nuevo_documento = Documento(
            nombre=nombre,
            url_documento=url_documento,
            fecha_subida=datetime.now().date(),
            etapa_id=etapa_id
        )
        
        db.add(nuevo_documento)
        await db.commit()
        await db.refresh(nuevo_documento)
        
        logger.info(f"Documento creado exitosamente: {nuevo_documento.id}")
        
        return {
            "ok": True,
            "data": {
                "id": nuevo_documento.id,
                "nombre": nuevo_documento.nombre,
                "url_documento": nuevo_documento.url_documento,
                "fecha_subida": str(nuevo_documento.fecha_subida),
                "hash": file_hash,
                "antivirus_escaneado": resultado_escaneo["escaneado"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        traceback.print_exc()
        logger.error(f"Error creando documento: {e}")
        raise HTTPException(status_code=500, detail="Error al crear documento")

@router.put("/{documento_id}")
async def actualizar_documento(
    request:Request,
    documento_id: int,
    radicado: str = Form(...),
    etapa_id: int = Form(...),

    nombre: str = Form(...),
    file: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Actualiza un documento existente.
    Incluye verificación de duplicados (SHA256) y escaneo antivirus (ClamAV) si se sube nuevo archivo.
    """
    try:
        usuario_id = verify_gateway_token(request)
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )

        stmt = select(Documento).where(Documento.id == documento_id)
        documento = await db.scalar(stmt)

        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")

        datos_anteriores = {
            "id": documento.id,
            "nombre": documento.nombre,
            "url_documento": documento.url_documento,
            "etapa_id": documento.etapa_id,
            "fecha_subida": str(documento.fecha_subida)
        }

        old_url = documento.url_documento
        nombre_sanitizado = "".join(c for c in nombre if c.isalnum() or c in (' ', '-', '_')).strip()
        nombre_sanitizado = nombre_sanitizado.replace(' ', '_')

        # Si se proporciona un nuevo archivo
        if file:
            # 1. Calcular hash
            logger.info(f"Calculando hash para nuevo archivo: {file.filename}")
            file_hash, file_data = calcular_hash_uploadfile(file)
            
            # 2. Validación completa de seguridad (Caso 8: 5 capas)
            logger.info(f"Validando seguridad del archivo: {file.filename}")
            max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
            
            try:
                validation_result = await validate_file_complete(
                    file_data=file_data,
                    filename=file.filename,
                    max_size_mb=max_size
                )
                sanitized_filename = validation_result["sanitized_filename"]
                mime_type = validation_result["mime_type"]
                logger.info(f"Validacion exitosa: {validation_result}")
            except HTTPException as e:
                logger.error(f"Validacion de seguridad fallo: {e.detail}")
                raise
            
            # 3. Verificar duplicados
            stmt_hash = select(Documento).where(
                Documento.etapa_id == etapa_id,
                Documento.id != documento_id  # Excluir el documento actual
            )
            result_docs = await db.execute(stmt_hash)
            documentos_existentes = result_docs.scalars().all()
            
            for doc_existente in documentos_existentes:
                if file_hash in doc_existente.url_documento:
                    logger.warning(f"Archivo duplicado detectado: {file_hash}")
                    raise HTTPException(
                        status_code=409,
                        detail=f"Este archivo ya existe en la etapa (documento: {doc_existente.nombre})"
                    )
            
            # 4. Escanear con ClamAV (Capa 4 de seguridad)
            logger.info(f"Escaneando archivo con ClamAV: {file.filename}")
            resultado_escaneo = escanear_archivo(file_data, file.filename)
            
            if not resultado_escaneo["ok"]:
                logger.error(f"Archivo rechazado por antivirus: {resultado_escaneo['mensaje']}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Archivo rechazado: {resultado_escaneo['mensaje']}"
                )

            # 5. Eliminar archivo antiguo de MinIO
            if old_url.startswith(MINIO_BUCKET + "/"):
                old_object_name = old_url.replace(MINIO_BUCKET + "/", "")
                logger.info(f"Eliminando archivo antiguo: {old_object_name}")
                delete_file_from_minio(old_object_name)

            # 6. Subir nuevo archivo a MinIO con deduplicación (usar nombre sanitizado)
            logger.info(f"Subiendo nuevo archivo a MinIO con deduplicación")
            resultado_upload = await upload_file_with_deduplication(
                db=db,
                file_data=file_data,
                original_filename=sanitized_filename,  # Usar nombre sanitizado
                content_type=mime_type  # Usar MIME detectado
            )
            
            if not resultado_upload["ok"]:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error subiendo archivo: {resultado_upload.get('message', 'Error desconocido')}"
                )

            documento.url_documento = resultado_upload["url"]
            
            if resultado_upload.get("deduplicated"):
                logger.info(f"Archivo duplicado - Documento actualizado - URL reutilizada: {documento.url_documento}")
            else:
                logger.info(f"Archivo nuevo - Documento actualizado: {documento.url_documento}")

        # Actualizar nombre
        documento.nombre = nombre

        datos_nuevos = {
            "id": documento.id,
            "nombre": documento.nombre,
            "url_documento": documento.url_documento,
            "etapa_id": documento.etapa_id,
            "archivo_reemplazado": file is not None
        }

        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="documento",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de documento ID {documento_id}: '{nombre}'",
            expediente_radicado=radicado,
            id_registro=str(documento_id),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        await db.commit()
        await db.refresh(documento)

        return {
            "ok": True,
            "data": {
                "id": documento.id,
                "nombre": documento.nombre,
                "url_documento": documento.url_documento,
                "fecha_subida": str(documento.fecha_subida)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error actualizando documento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{documento_id}")
async def eliminar_documento(
    request: Request,
    documento_id: int,
    radicado: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Elimina un documento y su archivo asociado de MinIO.
    """
    try:
        usuario_id = verify_gateway_token(request)
        stmt = select(Expediente.encargado_id).where(Expediente.radicado == radicado)
        encargado_id = await db.scalar(stmt)

        if not encargado_id:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para modificar este expediente"
            )
        
        stmt = select(Documento).where(Documento.id == documento_id)
        documento = await db.scalar(stmt)
        
        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        datos_anteriores = {
            "id": documento.id,
            "nombre": documento.nombre,
            "url_documento": documento.url_documento,
            "etapa_id": documento.etapa_id,
            "fecha_subida": str(documento.fecha_subida)
        }
        
        # Eliminar de MinIO
        if documento.url_documento.startswith(MINIO_BUCKET + "/"):
            object_name = documento.url_documento.replace(MINIO_BUCKET + "/", "")
            logger.info(f"Eliminando archivo de MinIO: {object_name}")
            resultado = delete_file_from_minio(object_name)
            
            if not resultado["ok"]:
                logger.warning(f"Error eliminando de MinIO: {resultado.get('message')}")
        
        await db.delete(documento)
        
        audit_result = await insert_log_auditoria(
            db=db,
            usuario_id=usuario_id,
            tabla_afectada="documento",
            tipo_operacion="DELETE",
            descripcion=f"Eliminación de documento ID {documento_id}: '{documento.nombre}'",
            expediente_radicado=radicado,
            id_registro=str(documento_id),
            datos_anteriores=datos_anteriores
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )
        
        await db.commit()
        
        logger.info(f"Documento eliminado exitosamente: {documento_id}")
        
        return {
            "ok": True,
            "message": "Documento eliminado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error eliminando documento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download")
async def descargar_archivo(
    request: Request,
    file_path: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Descarga o visualiza un documento PDF desde MinIO.
    """
    try:
        usuario_id = verify_gateway_token(request)
        # Decodificar ruta del query param
        file_path = unquote(file_path)
        
        logger.info(f"[DOWNLOAD] Ruta recibida: {file_path}")

        # Normalizar ruta: quitar prefijo del bucket si existe
        if file_path.startswith(MINIO_BUCKET + "/"):
            file_path = file_path.replace(MINIO_BUCKET + "/", "", 1)
        elif file_path.startswith("uploads/expedientes/"):
            file_path = file_path.replace("uploads/expedientes/", "expedientes/", 1)
        
        logger.info(f"[DOWNLOAD] Ruta normalizada: {file_path}")

        # Detectar formato de ruta
        path_parts = file_path.split("/")
        
        # Nuevo formato con deduplicación: files/{prefix}/{hash}.ext
        if path_parts[0] == "files" and len(path_parts) >= 3:
            # Sistema de deduplicación - archivo compartido
            # No verificamos permisos individuales por expediente
            # El archivo es accesible si está en file_hash
            logger.info(f"[DOWNLOAD] Usando sistema de deduplicación para: {file_path}")
        
        # Formato legacy: expedientes/{id_auxiliar}/tipo_doc/archivo.ext
        elif path_parts[0] == "expedientes" and len(path_parts) > 1:
            try:
                id_auxiliar = int(path_parts[1])
                
                # Verificar permisos para formato legacy
                stmt = select(Expediente.encargado_id).where(Expediente.id_auxiliar == id_auxiliar)
                encargado_id = await db.scalar(stmt)

                if not encargado_id:
                    raise HTTPException(status_code=404, detail="Expediente no encontrado")

                if encargado_id != usuario_id:
                    raise HTTPException(status_code=403, detail="No tiene permisos para acceder a este archivo")
                    
            except (ValueError, IndexError):
                raise HTTPException(status_code=400, detail="Ruta de archivo inválida")
        
        else:
            raise HTTPException(status_code=400, detail="Ruta de archivo inválida")

        # Descargar de MinIO
        logger.info(f"[DOWNLOAD] Descargando archivo de MinIO: {file_path}")
        resultado = get_file_from_minio(file_path)
        
        if not resultado["ok"]:
            logger.error(f"[DOWNLOAD] ERROR - No se pudo descargar archivo de MinIO")
            logger.error(f"[DOWNLOAD] Mensaje de error: {resultado.get('message', 'Sin mensaje')}")
            logger.error(f"[DOWNLOAD] Ruta intentada: {file_path}")
            logger.error(f"[DOWNLOAD] Bucket: {MINIO_BUCKET}")
            raise HTTPException(status_code=404, detail="Archivo no encontrado en MinIO")
        
        file_data = resultado["data"]
        filename = file_path.split("/")[-1]
        
        logger.info(f"[DOWNLOAD] Archivo descargado exitosamente: {filename} ({len(file_data)} bytes)")
        
        # Devolver PDF para visualizar en el navegador
        return StreamingResponse(
            iter([file_data]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"Error al descargar archivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error al descargar archivo: {e}")


@router.get("/download-all/{radicado}")
async def descargar_todos_documentos(
    request: Request,
    radicado: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Descarga todos los documentos de un expediente combinados en un único PDF.
    Los documentos se ordenan por etapa y se deduplican (documentos repetidos solo aparecen una vez).
    """
    try:
        usuario_id = verify_gateway_token(request)
        
        # Verificar que el expediente existe y obtener permisos
        stmt = select(Expediente.encargado_id, Expediente.id_auxiliar).where(
            Expediente.radicado == radicado
        )
        result = await db.execute(stmt)
        expediente = result.one_or_none()

        if not expediente:
            raise HTTPException(status_code=404, detail="Expediente no encontrado")

        encargado_id, id_auxiliar = expediente
        if encargado_id != usuario_id:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para acceder a este expediente"
            )

        logger.info(f"[DOWNLOAD-ALL] Iniciando descarga para expediente: {radicado}")

        # Orden de etapas según el frontend: 
        # Indagación(2), Medida(1), Inicio(9), Cesación(10), Cargos(4), 
        # Apertura(5), Cierre(11), Decisión(6), Recurso(12), Ejecución(7)
        orden_etapas = [2, 1, 9, 10, 4, 5, 11, 6, 12, 7]
        
        # Crear mapping de tipo_etapa_id a orden
        orden_map = {tipo_id: idx for idx, tipo_id in enumerate(orden_etapas)}
        
        # Obtener todas las etapas del expediente
        stmt = (
            select(Etapa.id, TipoEtapa.id.label("tipo_etapa_id"), TipoEtapa.nombre)
            .join(TipoEtapa, Etapa.tipo_etapa_id == TipoEtapa.id)
            .where(Etapa.expediente_radicado == radicado)
        )
        result = await db.execute(stmt)
        etapas_raw = result.all()
        
        # Ordenar etapas manualmente según el orden del frontend
        etapas = sorted(
            etapas_raw, 
            key=lambda e: orden_map.get(e[1], 999)  # 999 para etapas no mapeadas al final
        )

        if not etapas:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron etapas para este expediente"
            )

        logger.info(f"[DOWNLOAD-ALL] Encontradas {len(etapas)} etapas")

        # Conjunto para rastrear URLs únicas (deduplicación)
        urls_vistas = set()
        documentos_unicos = []  # Lista de tuplas (url, nombre_etapa, nombre_documento)

        # Recorrer etapas en orden y recolectar documentos
        for etapa_id, tipo_etapa_id, nombre_etapa in etapas:
            logger.info(f"[DOWNLOAD-ALL] Procesando etapa: {nombre_etapa} (ID: {etapa_id})")

            # 1. ACTO ADMINISTRATIVO
            stmt = select(ActoAdmin.id, ActoAdmin.url_acto, ActoAdmin.tipo_acto).where(
                ActoAdmin.etapa_id == etapa_id
            )
            result = await db.execute(stmt)
            actos = result.all()

            for acto_id, url_acto, tipo_acto in actos:
                if url_acto and url_acto not in urls_vistas:
                    urls_vistas.add(url_acto)
                    documentos_unicos.append((url_acto, nombre_etapa, f"Acto Administrativo - {tipo_acto}"))
                    logger.info(f"  ✓ Agregado acto administrativo: {tipo_acto}")

                # 2. COMUNICACIÓN O NOTIFICACIÓN (verificar cuál existe)
                
                # 2a. Verificar si tiene COMUNICACIÓN
                stmt_com = select(Comunicacion.url_documento).where(
                    Comunicacion.acto_admin_id == acto_id
                )
                result_com = await db.execute(stmt_com)
                comunicacion_url = result_com.scalar_one_or_none()

                if comunicacion_url:
                    if comunicacion_url not in urls_vistas:
                        urls_vistas.add(comunicacion_url)
                        documentos_unicos.append((comunicacion_url, nombre_etapa, "Comunicación"))
                        logger.info(f"  ✓ Agregado comunicación")
                else:
                    # 2b. Si no hay comunicación, verificar NOTIFICACIONES
                    stmt_not_id = select(Notificacion.id).where(
                        Notificacion.acto_admin_id == acto_id
                    )
                    result_not_id = await db.execute(stmt_not_id)
                    notificacion_id = result_not_id.scalar_one_or_none()

                    if notificacion_id:
                        # Obtener todos los involucrados notificados
                        stmt_inv_not = (
                            select(
                                InvolucradoNotificacion.url_doc_citacion,
                                InvolucradoNotificacion.url_documento,
                                Involucrado.nombre
                            )
                            .join(Involucrado, InvolucradoNotificacion.involucrado_id == Involucrado.id)
                            .where(InvolucradoNotificacion.notificacion_id == notificacion_id)
                        )
                        result_inv_not = await db.execute(stmt_inv_not)
                        involucrados_notificaciones = result_inv_not.all()

                        # Para cada involucrado: primero citación, luego notificación
                        for url_citacion, url_notificacion, nombre_involucrado in involucrados_notificaciones:
                            # Primero citación
                            if url_citacion and url_citacion not in urls_vistas:
                                urls_vistas.add(url_citacion)
                                documentos_unicos.append(
                                    (url_citacion, nombre_etapa, f"Citación - {nombre_involucrado}")
                                )
                                logger.info(f"  ✓ Agregado citación para {nombre_involucrado}")
                            
                            # Luego notificación
                            if url_notificacion and url_notificacion not in urls_vistas:
                                urls_vistas.add(url_notificacion)
                                documentos_unicos.append(
                                    (url_notificacion, nombre_etapa, f"Notificación - {nombre_involucrado}")
                                )
                                logger.info(f"  ✓ Agregado notificación para {nombre_involucrado}")

            # 3. DOCUMENTOS ANEXOS (ordenados por fecha de subida, más antigua primero)
            stmt = (
                select(Documento.url_documento, Documento.nombre, Documento.fecha_subida)
                .where(Documento.etapa_id == etapa_id)
                .order_by(Documento.fecha_subida.asc())
            )
            result = await db.execute(stmt)
            documentos_etapa = result.all()

            for url, nombre, fecha_subida in documentos_etapa:
                if url and url not in urls_vistas:
                    urls_vistas.add(url)
                    documentos_unicos.append((url, nombre_etapa, nombre or "Documento Anexo"))
                    logger.info(f"  ✓ Agregado documento anexo: {nombre} (fecha: {fecha_subida})")

        if not documentos_unicos:
            raise HTTPException(
                status_code=404,
                detail="No se encontraron documentos para este expediente"
            )

        logger.info(
            f"[DOWNLOAD-ALL] Total documentos únicos a combinar: {len(documentos_unicos)}"
        )

        # Crear PdfWriter para combinar PDFs
        pdf_writer = PdfWriter()
        documentos_procesados = 0

        # Descargar y agregar cada PDF
        for url, nombre_etapa, nombre_doc in documentos_unicos:
            try:
                # Normalizar URL (quitar prefijo del bucket si existe)
                file_path = url
                if file_path.startswith(MINIO_BUCKET + "/"):
                    file_path = file_path.replace(MINIO_BUCKET + "/", "", 1)
                elif file_path.startswith("uploads/expedientes/"):
                    file_path = file_path.replace("uploads/expedientes/", "expedientes/", 1)

                logger.info(f"  [DOWNLOAD] Intentando descargar: {nombre_doc}")
                logger.info(f"  [DOWNLOAD] URL original: {url}")
                logger.info(f"  [DOWNLOAD] Ruta normalizada: {file_path}")

                # Descargar de MinIO
                resultado = get_file_from_minio(file_path)
                
                if not resultado["ok"]:
                    logger.warning(f"  ⚠ [DOWNLOAD] ERROR - No se pudo descargar archivo de MinIO")
                    logger.warning(f"  ⚠ [DOWNLOAD] Mensaje: {resultado.get('message', 'Sin mensaje')}")
                    logger.warning(f"  ⚠ [DOWNLOAD] Ruta intentada: {file_path}")
                    logger.warning(f"  ⚠ [DOWNLOAD] URL original: {url}")
                    continue

                file_data = resultado["data"]

                # Agregar al PDF combinado
                pdf_reader = PdfReader(BytesIO(file_data))
                
                # Agregar todas las páginas del documento
                for page in pdf_reader.pages:
                    pdf_writer.add_page(page)
                
                documentos_procesados += 1
                logger.info(f"  ✓ [DOWNLOAD] Agregado exitosamente: {nombre_doc} ({len(pdf_reader.pages)} páginas)")

            except Exception as e:
                logger.warning(f"  ⚠ [DOWNLOAD] Excepción procesando documento")
                logger.warning(f"  ⚠ [DOWNLOAD] URL: {url}")
                logger.warning(f"  ⚠ [DOWNLOAD] Error: {str(e)}")
                logger.warning(f"  ⚠ [DOWNLOAD] Tipo de error: {type(e).__name__}")
                continue

        if documentos_procesados == 0:
            raise HTTPException(
                status_code=500,
                detail="No se pudo procesar ningún documento"
            )

        logger.info(
            f"[DOWNLOAD-ALL] Documentos procesados exitosamente: {documentos_procesados}/{len(documentos_unicos)}"
        )

        # Generar PDF final en memoria
        output_buffer = BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)

        # Nombre del archivo de salida
        filename = f"expediente_{radicado}_completo.pdf"

        logger.info(f"[DOWNLOAD-ALL] PDF generado exitosamente: {filename}")

        # Retornar PDF combinado
        return StreamingResponse(
            output_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"[DOWNLOAD-ALL] Error al generar PDF combinado: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar PDF combinado: {str(e)}"
        )
