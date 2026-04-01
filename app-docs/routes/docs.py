from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import logging
import asyncio
import json

from db.deps import get_db
from services.notificacion import (
    crear_notificacion_usuario,
    notificar_asignacion_revisor,
    notificar_nueva_version,
    notificar_documento_rechazado,
    notificar_documento_aprobado,
    notificar_documento_finalizado
)
from services.usuarios import obtener_usuarios_por_permiso
from utils.verify_token import verify_gateway_token
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

#--------- Modelos de BD ----------
from db.models.documentos import Documento
from db.models.versiones_documento import VersionDocumento
from db.models.asignaciones_revisores import AsignacionRevisor
from db.models.revisiones import Revision
from db.models.auditoria_documentos import AuditoriaDocumento
from db.models.v_documentos_detalle import VDocumentoDetalle

from core.permission import permission

PERMISO_CREADOR = permission.PERMISO_CREADOR
PERMISO_REVISOR = permission.PERMISO_REVISOR


load_dotenv()
router = APIRouter()
logger = logging.getLogger(__name__)

# URL del Gateway para comunicación entre servicios
GATEWAY_URL = os.getenv("GATEWAY_URL")

# Inicializar MinIO
init_minio()

class DocumentoResumen(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str]
    estado: str
    fecha_creacion: datetime
    fecha_ultima_actualizacion: datetime
    version_actual: Optional[int] = None
    numero_devoluciones: int
    usuario_creador_id: int
    total_revisiones: int
    total_revisores: int

    class Config:
        from_attributes = True

class VersionDocumentoSchema(BaseModel):
    version_id: int
    numero_version: int
    archivo_url: str
    archivo_nombre: str
    archivo_size: int
    fecha_subida: datetime
    comentario: Optional[str]

    class Config:
        from_attributes = True

class RevisionSchema(BaseModel):
    revision_id: int
    revisor_id: int
    estado: str
    comentarios: Optional[str]
    fecha_revision: datetime
    version_revisada: int

    class Config:
        from_attributes = True

class RevisorAsignado(BaseModel):
    revisor_id: int
    fecha_asignacion: datetime
    notificado: bool

    class Config:
        from_attributes = True

class AuditoriaItem(BaseModel):
    auditoria_id: int
    usuario_id: int
    accion: str
    descripcion: Optional[str]
    fecha_accion: datetime

    class Config:
        from_attributes = True

class DocumentoCompleto(BaseModel):
    documento_id: int
    nombre: str
    descripcion: Optional[str]
    tipo_archivo: str
    estado: str
    version_actual: int
    numero_devoluciones: int
    fecha_creacion: datetime
    versiones: List[VersionDocumentoSchema]
    revisiones: List[RevisionSchema]
    revisores_asignados: List[RevisorAsignado]
    auditoria: List[AuditoriaItem]

    class Config:
        from_attributes = True

# ------------- ENDPOINTS --------------

@router.get("/list", response_model=List[DocumentoResumen])
async def listar_documentos(
    request: Request,
    estado: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Lista documentos según los permisos del usuario:
    - CREADOR: Ve solo sus documentos creados
    - REVISOR: Ve documentos asignados para revisar
    
    Si tiene ambos permisos, ve todos los documentos relevantes.
    Filtros opcionales: estado, rango de fechas
    OPTIMIZACIÓN: Paginación implementada (page, page_size)
    """
    token_data = verify_gateway_token(request)
    usuario_id = int(token_data["user_id"])

    # Verificar permisos desde el token (sin llamadas HTTP)
    tiene_permiso_creador = PERMISO_CREADOR in token_data["permisos"]
    tiene_permiso_revisor = PERMISO_REVISOR in token_data["permisos"]

    if not tiene_permiso_creador and not tiene_permiso_revisor:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver documentos")
    
    # Construir query base
    stmt = select(VDocumentoDetalle)
    
    # Filtrar según permisos
    if tiene_permiso_creador and tiene_permiso_revisor:
        # Ve sus documentos + asignados como revisor
        subquery = select(AsignacionRevisor.documento_id).where(
            AsignacionRevisor.revisor_id == usuario_id
        )
        stmt = stmt.where(
            or_(
                VDocumentoDetalle.usuario_creador_id == usuario_id,
                VDocumentoDetalle.id.in_(subquery)
            )
        )
    elif tiene_permiso_creador:
        # Solo ve sus documentos
        stmt = stmt.where(VDocumentoDetalle.usuario_creador_id == usuario_id)
    elif tiene_permiso_revisor:
        # Solo ve documentos asignados
        subquery = select(AsignacionRevisor.documento_id).where(
            AsignacionRevisor.revisor_id == usuario_id
        )
        stmt = stmt.where(VDocumentoDetalle.id.in_(subquery))
    
    # Aplicar filtros opcionales
    if estado:
        stmt = stmt.where(VDocumentoDetalle.estado == estado)
    if fecha_desde:
        stmt = stmt.where(VDocumentoDetalle.fecha_creacion >= fecha_desde)
    if fecha_hasta:
        stmt = stmt.where(VDocumentoDetalle.fecha_creacion <= fecha_hasta)
    
    # Ordenar y aplicar paginación
    stmt = stmt.order_by(VDocumentoDetalle.fecha_creacion.desc())
    
    # Aplicar LIMIT y OFFSET para paginación
    offset = (page - 1) * page_size
    stmt = stmt.limit(page_size).offset(offset)
    
    result = await db.execute(stmt)
    documentos = result.scalars().all()
    
    # Eliminar duplicados basados en id del documento
    documentos_unicos = {}
    for doc in documentos:
        if doc.id not in documentos_unicos:
            documentos_unicos[doc.id] = doc
    
    return list(documentos_unicos.values())

@router.get("/detail/{documento_id}")
async def obtener_documento_completo(
    request: Request,
    documento_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene toda la información del documento incluyendo:
    - Historial de versiones
    - Revisiones realizadas
    - Revisores asignados
    - Auditoría completa
    """
    try:
        token_data = verify_gateway_token(request)
        usuario_id = int(token_data["user_id"])

        # Verificar permisos desde el token (sin llamadas HTTP)
        tiene_permiso_creador = PERMISO_CREADOR in token_data["permisos"]
        tiene_permiso_revisor = PERMISO_REVISOR in token_data["permisos"]

        if not tiene_permiso_creador and not tiene_permiso_revisor:
            raise HTTPException(status_code=403, detail="No tienes permisos para ver documentos")
        
        # OPTIMIZACIÓN: Cargar documento con relaciones usando selectinload
        stmt = (
            select(Documento)
            .options(
                selectinload(Documento.versiones),
                selectinload(Documento.revisiones),
                selectinload(Documento.asignaciones_revisores),
                selectinload(Documento.auditoria)
            )
            .where(Documento.id == documento_id)
        )
        result = await db.execute(stmt)
        documento = result.scalar_one_or_none()
        
        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        # Verificar acceso específico al documento
        es_creador = documento.usuario_creador_id == usuario_id
        es_revisor = any(a.revisor_id == usuario_id for a in documento.asignaciones_revisores)
        
        if not es_creador and not es_revisor:
            raise HTTPException(status_code=403, detail="No tienes acceso a este documento")
        
        # Los datos ya están cargados por selectinload
        versiones = sorted(documento.versiones, key=lambda v: v.numero_version, reverse=True)
        revisiones = sorted(documento.revisiones, key=lambda r: r.fecha_revision, reverse=True)
        revisores_asignados = sorted(documento.asignaciones_revisores, key=lambda a: a.fecha_asignacion)
        auditoria_raw = sorted(documento.auditoria, key=lambda a: a.fecha_accion)
        
        # Obtener nombres de revisores (con caché)
        revisores_ids = set([r.revisor_id for r in revisiones])
        revisores_info = {}
        if revisores_ids:
            revisores_data = await obtener_usuarios_por_permiso(PERMISO_REVISOR)
            revisores_info = {uid: info for uid, info in revisores_data.items() if uid in revisores_ids}
        
        # Consolidar eventos de auditoría duplicados
        # Agrupar por acción + fecha (mismo minuto) y quedarse con la descripción más completa
        from collections import defaultdict
        eventos_agrupados = defaultdict(list)
        
        for a in auditoria_raw:
            # Clave: acción + fecha truncada al minuto
            fecha_minuto = a.fecha_accion.replace(second=0, microsecond=0)
            key = (a.accion, fecha_minuto)
            eventos_agrupados[key].append(a)
        
        # Consolidar eventos duplicados quedándose con la descripción más larga/completa
        auditoria_consolidada = []
        for (accion, fecha_minuto), eventos in eventos_agrupados.items():
            # Ordenar por: 1) longitud de descripción (desc), 2) fecha más reciente
            eventos_ordenados = sorted(
                eventos, 
                key=lambda e: (len(e.descripcion or ""), e.fecha_accion),
                reverse=True
            )
            # Tomar el evento con la descripción más completa
            auditoria_consolidada.append(eventos_ordenados[0])
        
        # Ordenar por fecha
        auditoria = sorted(auditoria_consolidada, key=lambda x: x.fecha_accion)
        
        # Construir respuesta completa
        documento_completo = {
            "ok": True,
            "documento_id": documento.id,
            "nombre": documento.nombre,
            "descripcion": documento.descripcion or "",
            "tipo_archivo": documento.tipo_archivo,
            "estado": documento.estado,
            "version_actual": documento.version_actual or 1,  # ← Default a 1 si es None
            "numero_devoluciones": documento.numero_devoluciones or 0,
            "fecha_creacion": documento.fecha_creacion.isoformat() if documento.fecha_creacion else None,
            "usuario_creador_id": documento.usuario_creador_id,
            "versiones": [
                {
                    "version_id": v.id,
                    "numero_version": v.numero_version,
                    "archivo_url": v.archivo_url,
                    "archivo_nombre": v.archivo_nombre_original,
                    "archivo_size": v.archivo_size or 0,
                    "fecha_subida": v.fecha_subida.isoformat() if v.fecha_subida else None,
                    "comentario": v.comentario or ""
                }
                for v in versiones
            ],
            "revisiones": [
                {
                    "revision_id": r.id,
                    "revisor_id": r.revisor_id,
                    "revisor_nombre": revisores_info.get(r.revisor_id, {}).get("nombre", f"Usuario {r.revisor_id}"),
                    "estado": r.estado_revision,
                    "comentarios": r.comentarios or "",
                    "fecha_revision": r.fecha_revision.isoformat() if r.fecha_revision else None,
                    "version_revisada": r.version_revisada
                }
                for r in revisiones
            ],
            "revisores_asignados": [
                {
                    "revisor_id": ra.revisor_id,
                    "fecha_asignacion": ra.fecha_asignacion.isoformat() if ra.fecha_asignacion else None,
                    "notificado": ra.notificado if ra.notificado is not None else False
                }
                for ra in revisores_asignados
            ],
            "auditoria": [
                {
                    "auditoria_id": a.id,
                    "usuario_id": a.usuario_id,
                    "accion": a.accion,
                    "descripcion": a.descripcion or "",
                    "fecha_accion": a.fecha_accion.isoformat() if a.fecha_accion else None
                }
                for a in auditoria
            ]
        }
        
        logger.info("Documento completo construido exitosamente")
        return documento_completo
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo documento completo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/create")
async def crear_documento(
    request: Request,
    nombre: str = Form(...),
    descripcion: str = Form(None),
    tipo_archivo: str = Form(...),
    revisores_ids: str = Form(...),  # JSON string: "[1,2,3]"
    archivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Crea un nuevo documento y lo asigna a revisores.
    Requiere permiso: PERMISO_CREADOR
    """
    token_data = verify_gateway_token(request)
    usuario_creador_id = int(token_data["user_id"])

    # Verificar permiso de creador
    if PERMISO_CREADOR not in token_data["permisos"]:
        raise HTTPException(status_code=403, detail="No tienes permiso para crear documentos")
    
    # Validar tipo de archivo
    if tipo_archivo not in ['pdf', 'docx', 'doc']:
        raise HTTPException(status_code=400, detail="Tipo de archivo no válido (pdf, docx, doc)")
    
    # Parsear revisores
    try:
        revisores_list = json.loads(revisores_ids)
    except:
        raise HTTPException(status_code=400, detail="Formato de revisores inválido")
    
    if not revisores_list:
        raise HTTPException(status_code=400, detail="Debe asignar al menos un revisor")
    
    # Verificar que los revisores tienen el permiso correcto
    for revisor_id in revisores_list:
        try:
            result = await verificar_permiso_externo(revisor_id, PERMISO_REVISOR)
            if not result.get("ok", False):
                raise HTTPException(
                    status_code=400, 
                    detail=f"El usuario {revisor_id} no tiene permiso de revisor"
                )
        except HTTPException:
            raise
        except:
            raise HTTPException(
                status_code=400, 
                detail=f"No se pudo verificar el usuario {revisor_id}"
            )
    
    # 1. Calcular hash SHA256
    logger.info(f"Calculando hash para archivo: {archivo.filename}")
    file_hash, file_data = calcular_hash_uploadfile(archivo)
    archivo_size = len(file_data)
    
    # 2. Validación completa de seguridad (Caso 8: 5 capas)
    logger.info(f"Validando seguridad del archivo: {archivo.filename}")
    max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    
    try:
        validation_result = await validate_file_complete(
            file_data=file_data,
            filename=archivo.filename,
            max_size_mb=max_size
        )
        sanitized_filename = validation_result["sanitized_filename"]
        mime_type = validation_result["mime_type"]
        logger.info(f"Validacion exitosa: {validation_result}")
    except HTTPException as e:
        logger.error(f"Validacion de seguridad fallo: {e.detail}")
        raise
    
    # 3. Verificar duplicados
    # Buscar documentos del mismo usuario con el mismo hash
    stmt_hash = select(VersionDocumento).join(
        Documento, VersionDocumento.documento_id == Documento.id
    ).where(
        Documento.usuario_creador_id == usuario_creador_id
    )
    result_docs = await db.execute(stmt_hash)
    versiones_existentes = result_docs.scalars().all()
    
    for version_existente in versiones_existentes:
        if file_hash in version_existente.archivo_url:
            logger.warning(f"Archivo duplicado detectado: {file_hash}")
            raise HTTPException(
                status_code=409,
                detail="Este archivo ya fue subido anteriormente"
            )
    
    # 4. Escanear con ClamAV (Capa 4 de seguridad)
    logger.info(f"Escaneando archivo con ClamAV: {archivo.filename}")
    resultado_escaneo = escanear_archivo(file_data, archivo.filename)
    
    if not resultado_escaneo["ok"]:
        logger.error(f"Archivo rechazado por antivirus: {resultado_escaneo['mensaje']}")
        raise HTTPException(
            status_code=400,
            detail=f"Archivo rechazado: {resultado_escaneo['mensaje']}"
        )
    
    # 5. Subir a MinIO con deduplicación (usar nombre sanitizado y MIME detectado)
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
    
    archivo_url = resultado_upload["url"]
    
    if resultado_upload.get("deduplicated"):
        logger.info(f"Archivo duplicado - URL reutilizada: {archivo_url}")
    else:
        logger.info(f"Archivo nuevo subido: {archivo_url}")
    
    # 5. Crear documento en BD
    nuevo_documento = Documento(
        nombre=nombre,
        descripcion=descripcion,
        tipo_archivo=tipo_archivo,
        usuario_creador_id=usuario_creador_id,
        estado='en_revision',
        version_actual=1
    )
    db.add(nuevo_documento)
    await db.flush()
    
    # 6. Crear primera versión
    nueva_version = VersionDocumento(
        documento_id=nuevo_documento.id,
        numero_version=1,
        archivo_url=archivo_url,
        archivo_nombre_original=archivo.filename,
        archivo_size=archivo_size,
        usuario_subida_id=usuario_creador_id,
        comentario="Versión inicial"
    )
    db.add(nueva_version)
    
    # 7. Asignar revisores y enviar notificaciones
    for revisor_id in revisores_list:
        asignacion = AsignacionRevisor(
            documento_id=nuevo_documento.id,
            revisor_id=revisor_id,
            notificado=True
        )
        db.add(asignacion)
        
        # Enviar notificación usando función helper
        logger.info(f"Notificando a revisor {revisor_id} del documento {nuevo_documento.id}")
        try:
            resultado_notif = await notificar_asignacion_revisor(
                documento_id=nuevo_documento.id,
                documento_nombre=nombre,
                revisor_id=revisor_id,
                version_actual=1
            )
            logger.info(f"Notificación enviada a revisor {revisor_id}: {resultado_notif}")
        except Exception as e:
            logger.error(f"Error al notificar revisor {revisor_id}: {e}")
    
    # 8. Registrar en auditoría
    auditoria = AuditoriaDocumento(
        documento_id=nuevo_documento.id,
        usuario_id=usuario_creador_id,
        accion='crear',
        descripcion=f'Documento creado con {len(revisores_list)} revisor(es)',
        datos_adicionales={'revisores': revisores_list, 'hash': file_hash[:16]}
    )
    db.add(auditoria)
    
    await db.commit()
    
    logger.info(f"Documento creado exitosamente: {nuevo_documento.id}")
    
    return {
        "ok": True,
        "documento_id": nuevo_documento.id,
        "hash": file_hash,
        "antivirus_escaneado": resultado_escaneo["escaneado"],
        "message": "Documento creado exitosamente"
    }

@router.post("/upload-version/{documento_id}")
async def subir_nueva_version(
    request: Request,
    documento_id: int,
    comentario: str = Form(None),
    archivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Sube una nueva versión del documento tras una devolución.
    Requiere permiso: PERMISO_CREADOR_DOC

    """
    try:
        token_data = verify_gateway_token(request)
        usuario_id = int(token_data["user_id"])

        # Verificar permiso
        if PERMISO_CREADOR not in token_data["permisos"]:
            raise HTTPException(status_code=403, detail="No tienes permiso para subir documentos")
        
        stmt = select(Documento).where(Documento.id == documento_id)
        result = await db.execute(stmt)
        documento = result.scalar_one_or_none()
        
        if not documento:
            raise HTTPException(status_code=404, detail="Documento no encontrado")
        
        if documento.usuario_creador_id != usuario_id:
            raise HTTPException(status_code=403, detail="No eres el creador de este documento")
        
        # Solo permitir subir versiones si el documento está rechazado
        if documento.estado != 'rechazado':
            raise HTTPException(
                status_code=400, 
                detail="Solo puedes subir una nueva versión cuando el documento ha sido devuelto"
            )
        
        # 1. Calcular hash SHA256
        logger.info(f"Calculando hash para nueva versión: {archivo.filename}")
        file_hash, file_data = calcular_hash_uploadfile(archivo)
        archivo_size = len(file_data)
        
        # 2. Validación completa de seguridad (Caso 8: 5 capas)
        logger.info(f"Validando seguridad del archivo: {archivo.filename}")
        max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
        
        try:
            validation_result = await validate_file_complete(
                file_data=file_data,
                filename=archivo.filename,
                max_size_mb=max_size
            )
            sanitized_filename = validation_result["sanitized_filename"]
            mime_type = validation_result["mime_type"]
            logger.info(f"Validacion exitosa: {validation_result}")
        except HTTPException as e:
            logger.error(f"Validacion de seguridad fallo: {e.detail}")
            raise
        
        # 3. Verificar duplicados
        stmt_hash = select(VersionDocumento).where(
            VersionDocumento.documento_id == documento_id
        )
        result_versions = await db.execute(stmt_hash)
        versiones_existentes = result_versions.scalars().all()
        
        for version_existente in versiones_existentes:
            if file_hash in version_existente.archivo_url:
                logger.warning(f"Archivo duplicado detectado: {file_hash}")
                raise HTTPException(
                    status_code=409,
                    detail="Esta versión del archivo ya existe en el documento"
                )
        
        # 4. Escanear con ClamAV (Capa 4 de seguridad)
        logger.info(f"Escaneando archivo con ClamAV: {archivo.filename}")
        resultado_escaneo = escanear_archivo(file_data, archivo.filename)
        
        if not resultado_escaneo["ok"]:
            logger.error(f"Archivo rechazado por antivirus: {resultado_escaneo['mensaje']}")
            raise HTTPException(
                status_code=400,
                detail=f"Archivo rechazado: {resultado_escaneo['mensaje']}"
            )
        
        # 5. Subir a MinIO con deduplicación (usar nombre sanitizado y MIME detectado)
        logger.info(f"Subiendo nueva versión a MinIO con deduplicación")
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
        
        archivo_url = resultado_upload["url"]
        
        if resultado_upload.get("deduplicated"):
            logger.info(f"Archivo duplicado - URL reutilizada: {archivo_url}")
        else:
            logger.info(f"Archivo nuevo subido: {archivo_url}")
        
        # 5. Crear nueva versión
        nueva_version_num = documento.version_actual + 1
        nueva_version = VersionDocumento(
            documento_id=documento_id,
            numero_version=nueva_version_num,
            archivo_url=archivo_url,
            archivo_nombre_original=archivo.filename,
            archivo_size=archivo_size,
            usuario_subida_id=usuario_id,
            comentario=comentario
        )
        db.add(nueva_version)
        
        # 6. Actualizar documento
        documento.version_actual = nueva_version_num
        documento.estado = 'en_revision'
        documento.fecha_ultima_actualizacion = datetime.now()
        
        # 7. Notificar a revisores
        stmt_revisores = select(AsignacionRevisor).where(
            AsignacionRevisor.documento_id == documento_id
        )
        result_revisores = await db.execute(stmt_revisores)
        revisores = result_revisores.scalars().all()
        
        revisores_ids = [r.revisor_id for r in revisores]
        await notificar_nueva_version(
            documento_id=documento_id,
            documento_nombre=documento.nombre,
            version_numero=nueva_version_num,
            revisores_ids=revisores_ids
        )
        
        await db.commit()
        
        logger.info(f"Nueva version subida exitosamente: v{nueva_version_num}")
        
        return {
            "ok": True, 
            "version": nueva_version_num,
            "hash": file_hash,
            "antivirus_escaneado": resultado_escaneo["escaneado"],
            "message": "Versión subida exitosamente"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al subir versión: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al subir versión: {str(e)}"
        )

@router.post("/review/{documento_id}")
async def revisar_documento(
    request: Request,
    documento_id: int,
    estado_revision: str = Form(...),  # 'aprobado' o 'devuelto'
    comentarios: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Permite a un revisor aprobar o devolver un documento.
    Requiere permiso: PERMISO_REVISION_DOC
    
    - Si aprueba: estado -> 'aprobado'
    - Si devuelve: incrementa contador de devoluciones
    - Si llega a 3 devoluciones: estado -> 'finalizado'
    """
    token_data = verify_gateway_token(request)
    revisor_id = int(token_data["user_id"])  # El revisor es el usuario autenticado

    # Verificar permiso del usuario autenticado
    if PERMISO_REVISOR not in token_data["permisos"]:
        raise HTTPException(status_code=403, detail="No tienes permiso para revisar documentos")
    
    # Verificar que el usuario autenticado está asignado como revisor
    stmt_asignacion = select(AsignacionRevisor).where(
        and_(
            AsignacionRevisor.documento_id == documento_id,
            AsignacionRevisor.revisor_id == revisor_id
        )
    )
    result_asignacion = await db.execute(stmt_asignacion)
    asignacion = result_asignacion.scalar_one_or_none()
    
    if not asignacion:
        raise HTTPException(status_code=403, detail="No estás asignado como revisor de este documento")
    
    stmt_doc = select(Documento).where(Documento.id == documento_id)
    result_doc = await db.execute(stmt_doc)
    documento = result_doc.scalar_one_or_none()
    
    if not documento:
        raise HTTPException(status_code=404, detail="Documento no encontrado")
    
    if documento.estado != 'en_revision':
        raise HTTPException(status_code=400, detail="El documento no está en revisión")
    
    # Validar estado
    if estado_revision not in ['aprobado', 'devuelto']:
        raise HTTPException(status_code=400, detail="Estado de revisión inválido")
    
    # Crear registro de revisión
    nueva_revision = Revision(
        documento_id=documento_id,
        version_revisada=documento.version_actual,
        revisor_id=revisor_id,
        estado_revision=estado_revision,
        comentarios=comentarios
    )
    db.add(nueva_revision)
    
    # Actualizar estado del documento
    if estado_revision == 'aprobado':
        documento.estado = 'aprobado'
        accion_auditoria = 'aprobar'
        mensaje = "Documento aprobado exitosamente"
        
        # Notificar al creador
        await notificar_documento_aprobado(
            documento_id=documento_id,
            documento_nombre=documento.nombre,
            creador_id=documento.usuario_creador_id
        )
        
    else:  # devuelto
        documento.numero_devoluciones += 1
        
        if documento.numero_devoluciones >= 3:
            documento.estado = 'finalizado'
            accion_auditoria = 'finalizar'
            mensaje = "Documento finalizado tras 3 devoluciones"
            
            # Notificar al creador
            await notificar_documento_finalizado(
                documento_id=documento_id,
                documento_nombre=documento.nombre,
                creador_id=documento.usuario_creador_id
            )
        else:
            documento.estado = 'rechazado'
            accion_auditoria = 'devolver'
            mensaje = f"Estado cambiado de en_revision a rechazado, rechazos {documento.numero_devoluciones}/3"
            
            # Notificar al creador
            await notificar_documento_rechazado(
                documento_id=documento_id,
                documento_nombre=documento.nombre,
                creador_id=documento.usuario_creador_id,
                numero_devoluciones=documento.numero_devoluciones
            )
    
    documento.fecha_ultima_actualizacion = datetime.now()
    
    # Auditoría
    auditoria = AuditoriaDocumento(
        documento_id=documento_id,
        usuario_id=revisor_id,
        accion=accion_auditoria,
        descripcion=mensaje,
        datos_adicionales={'comentarios': comentarios, 'version': documento.version_actual}
    )
    db.add(auditoria)
    
    await db.commit()
    
    return {
        "ok": True,
        "estado": documento.estado,
        "numero_devoluciones": documento.numero_devoluciones,
        "message": mensaje
    }

@router.get("/download/{version_id}")
async def descargar_archivo(
    request: Request,
    version_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Descarga un archivo de una versión específica desde MinIO.
    Valida permisos antes de permitir la descarga.
    """
    try:
        token_data = verify_gateway_token(request)
        usuario_id = int(token_data["user_id"])

        stmt = select(VersionDocumento).where(VersionDocumento.id == version_id)
        result = await db.execute(stmt)
        version = result.scalar_one_or_none()
        
        if not version:
            raise HTTPException(status_code=404, detail="Versión no encontrada")
        
        # Verificar permisos
        stmt_doc = select(Documento).where(Documento.id == version.documento_id)
        result_doc = await db.execute(stmt_doc)
        documento = result_doc.scalar_one_or_none()
        
        es_creador = documento.usuario_creador_id == usuario_id
        
        stmt_revisor = select(AsignacionRevisor).where(
            and_(
                AsignacionRevisor.documento_id == version.documento_id,
                AsignacionRevisor.revisor_id == usuario_id
            )
        )
        result_revisor = await db.execute(stmt_revisor)
        es_revisor = result_revisor.scalar_one_or_none() is not None
        
        if not (es_creador or es_revisor):
            raise HTTPException(status_code=403, detail="No tienes permiso para descargar este archivo")
        
        # Descargar de MinIO
        # Quitar prefijo del bucket si existe
        file_path = version.archivo_url
        if file_path.startswith(MINIO_BUCKET + "/"):
            file_path = file_path.replace(MINIO_BUCKET + "/", "", 1)
        
        logger.info(f"Descargando archivo de MinIO: {file_path}")
        resultado = get_file_from_minio(file_path)
        
        if not resultado["ok"]:
            logger.error(f"Error descargando de MinIO: {resultado.get('message')}")
            raise HTTPException(status_code=404, detail="Archivo no encontrado en MinIO")
        
        file_data = resultado["data"]
        
        # Detectar content type
        content_types = {
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword'
        }
        content_type = content_types.get(documento.tipo_archivo, 'application/octet-stream')
        
        # Devolver archivo para descarga
        return StreamingResponse(
            iter([file_data]),
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{version.archivo_nombre_original}"'
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al descargar archivo: {e}")
        raise HTTPException(status_code=500, detail=f"Error al descargar archivo: {str(e)}")

@router.get("/stats")
async def obtener_estadisticas(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene estadísticas del usuario según sus permisos:
    - CREADOR: Documentos creados, aprobados, en revisión, finalizados
    - REVISOR: Documentos por revisar, revisados, pendientes
    
    OPTIMIZACIÓN: Verificación de permisos en paralelo y queries optimizadas con CASE
    """
    token_data = verify_gateway_token(request)
    usuario_id = int(token_data["user_id"])

    stats = {}
    
    # Verificar permisos desde el token (sin llamadas HTTP)
    tiene_permiso_creador = PERMISO_CREADOR in token_data["permisos"]
    tiene_permiso_revisor = PERMISO_REVISOR in token_data["permisos"]
    
    # OPTIMIZACIÓN: Estadísticas de creador en UNA SOLA query usando CASE
    if tiene_permiso_creador:
        try:
            from sqlalchemy import case
            stmt = select(
                func.count(Documento.id).label('total_creados'),
                func.sum(case((Documento.estado == 'en_revision', 1), else_=0)).label('en_revision'),
                func.sum(case((Documento.estado == 'aprobado', 1), else_=0)).label('aprobados'),
                func.sum(case((Documento.estado == 'rechazado', 1), else_=0)).label('rechazados'),
                func.sum(case((Documento.estado == 'finalizado', 1), else_=0)).label('finalizados')
            ).where(Documento.usuario_creador_id == usuario_id)
            
            result = await db.execute(stmt)
            row = result.one()
            
            stats["creador"] = {
                "total_creados": row.total_creados or 0,
                "en_revision": row.en_revision or 0,
                "aprobados": row.aprobados or 0,
                "rechazados": row.rechazados or 0,
                "finalizados": row.finalizados or 0
            }
        except Exception as e:
            logger.error(f"Error obteniendo stats de creador: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas de creador: {str(e)}")

    # OPTIMIZACIÓN: Estadísticas de revisor optimizadas
    if tiene_permiso_revisor:
        try:
            from sqlalchemy import case
            
            # Documentos asignados
            docs_asignados = select(AsignacionRevisor.documento_id).where(
                AsignacionRevisor.revisor_id == usuario_id
            ).scalar_subquery()
            
            # Stats de documentos asignados en UNA query
            stmt_docs = select(
                func.count(Documento.id).label('total_asignados'),
                func.sum(case((Documento.estado == 'en_revision', 1), else_=0)).label('pendientes')
            ).where(Documento.id.in_(docs_asignados))
            
            result_docs = await db.execute(stmt_docs)
            row_docs = result_docs.one()
            
            # Stats de revisiones en UNA query
            stmt_rev = select(
                func.count(Revision.id).label('total_revisiones'),
                func.sum(case((Revision.estado_revision == 'aprobado', 1), else_=0)).label('aprobados'),
                func.sum(case((Revision.estado_revision == 'devuelto', 1), else_=0)).label('devueltos')
            ).where(Revision.revisor_id == usuario_id)
            
            result_rev = await db.execute(stmt_rev)
            row_rev = result_rev.one()
            
            stats["revisor"] = {
                "total_asignados": row_docs.total_asignados or 0,
                "pendientes": row_docs.pendientes or 0,
                "total_revisiones": row_rev.total_revisiones or 0,
                "aprobados": row_rev.aprobados or 0,
                "devueltos": row_rev.devueltos or 0
            }
        except Exception as e:
            logger.error(f"Error obteniendo stats de revisor: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas de revisor: {str(e)}")

    if not stats:
        raise HTTPException(status_code=403, detail="No tienes permisos en este módulo")
    
    return {"ok": True, "stats": stats}

@router.get("/reviewers")
async def listar_revisores_disponibles(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene la lista de usuarios con permiso de revisor.
    
    Este endpoint:
    1. Valida el token del usuario (verify_gateway_token)
    2. Verifica que tenga permiso de creador O revisor
    3. Llama internamente al servicio de usuarios con token de servicio
    4. Retorna la lista de revisores disponibles
    
    Requiere permiso: PERMISO_CREADOR_DOC o PERMISO_REVISOR_DOC
    OPTIMIZACIÓN: Verificación de permisos en paralelo
    """
    token_data = verify_gateway_token(request)
    
    # Verificar permisos desde el token (sin llamadas HTTP)
    tiene_acceso = (
        PERMISO_CREADOR in token_data["permisos"] or
        PERMISO_REVISOR in token_data["permisos"]
    )

    if not tiene_acceso:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para consultar revisores. Se requiere permiso de creador o revisor."
        )
    
    # Obtener revisores usando la función helper
    try:
        revisores_dict = await obtener_usuarios_por_permiso(PERMISO_REVISOR)
        
        # Convertir el diccionario a lista para el frontend
        revisores_list = [
            {
                "id": user_id,
                "nombre_completo": info["nombre"],
                "email": info["correo"]
            }
            for user_id, info in revisores_dict.items()
        ]
        
        return {
            "ok": True,
            "usuarios": revisores_list,
            "total": len(revisores_list)
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo revisores: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error al obtener la lista de revisores"
        )