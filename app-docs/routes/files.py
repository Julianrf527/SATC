from utils.verify_token import verify_gateway_token, verify_service_token
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from minio.error import S3Error
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from pydantic import BaseModel, Field
import asyncio
import logging
import os
import tempfile

from db.deps import get_db_managed
from db.models.file_hash import FileHash
from utils.minio_client import upload_file_with_deduplication, abrir_objeto, descargar_a_archivo, tamano_objeto
from utils.descarga import (
    RangoNoSatisfacible,
    cabeceras_seguridad,
    etag,
    iterar_objeto,
    parse_range,
    rango_vigente,
    tipo_y_disposicion,
)
from utils.file_validator import validate_file_complete
from utils.antivirus import escanear_archivo
from core.permission import PERMISOS_ARCHIVOS
from services.users import verify_permission
from services.uso_archivos import (
    MODO_VALIDACION,
    UsoArchivo,
    aplicar_usos,
    nombre_servicio,
    quitar_usos,
    validar_asociacion,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Fase 4 del acceso a archivos. Con "false", GET /files/{id} y
# /files/download/{id} solo aceptan service-token: el usuario descarga por el
# endpoint de su módulo (/<modulo>/archivos/{id}), que valida que pueda ver la
# entidad dueña. Apagar solo cuando todos los módulos y el front lo usen.
ACCESO_DIRECTO_USUARIOS = os.getenv("ARCHIVOS_ACCESO_DIRECTO_USUARIOS", "true").strip().lower() != "false"


def exigir_acceso_directo(acceso: "Acceso", file_id: int) -> None:
    """Lectura de archivos por gateway: solo mientras siga habilitada. Cada
    lectura directa queda en el log ("Acceso directo de usuario") para medir
    cuándo se puede cerrar sin romper pantallas."""
    if acceso.servicio != "gateway":
        return
    if not ACCESO_DIRECTO_USUARIOS:
        raise HTTPException(status_code=403, detail="Descarga el archivo desde el módulo al que pertenece")
    logger.info(f"Acceso directo de usuario: usuario={acceso.usuario_id} file_id={file_id}")

class FilesBatchRequest(BaseModel):
    file_ids: List[int]

class FileStateUpdateRequest(BaseModel):
    """Formato actual: ``file_ids`` (solo mueve numero_usos). Formato nuevo:
    ``usos`` con la entidad dueña (+ ``usuario_id`` de quien asocia)."""
    file_ids: Optional[List[int]] = None
    usos: Optional[List[UsoArchivo]] = Field(default=None, max_length=500)
    usuario_id: Optional[int] = None


class RegistrarUsosRequest(BaseModel):
    usos: List[UsoArchivo] = Field(min_length=1, max_length=1000)


class Acceso(BaseModel):
    """Quién llama: ``servicio`` (nombre corto, 'gateway' si es un usuario) y
    el usuario cuando lo hay."""
    servicio: str
    usuario_id: Optional[int] = None


async def verify_internal_access(request: Request) -> Acceso:
    """
    Service-token (otro microservicio, sin usuario) o gateway-token más AL
    MENOS UN permiso de módulo con archivos (PERMISOS_ARCHIVOS).

    Los IDs de archivo son secuenciales: sin el permiso, cualquier usuario
    autenticado podría recorrer todos los archivos del sistema. Esto no
    verifica a qué expediente pertenece el archivo (app-docs no lo sabe); es
    el control provisional hasta tener URLs firmadas por el servicio dueño.
    """
    service_token = request.headers.get("x-service-token")
    gateway_token = request.headers.get("x-gateway-token")

    if service_token:
        return Acceso(servicio=nombre_servicio(verify_service_token(request)))
    elif gateway_token:
        user_id = verify_gateway_token(request)["user_id"]
        for permiso in PERMISOS_ARCHIVOS:
            if await verify_permission(user_id, permiso):
                return Acceso(servicio="gateway", usuario_id=user_id)
        raise HTTPException(status_code=403, detail="No tiene permisos para acceder a archivos")
    else:
        raise HTTPException(status_code=401, detail="No se proporcionó token de autenticación")

def verify_service_only_access(request: Request) -> str:
    """
    Para endpoints exclusivamente service-to-service (nunca llamados desde el
    frontend vía gateway): exige X-Service-Token estricto, sin fallback a
    X-Gateway-Token. El gateway inyecta X-Gateway-Token en toda petición que
    reenvía, incluidas las que no exigen sesión de usuario — aceptarlo acá
    permitiría a cualquiera con acceso a la red interna suplantar un servicio.

    Devuelve el nombre corto del servicio que llama ('infraction', 'recurso'...).
    """
    return nombre_servicio(verify_service_token(request))

@router.post("/upload")
async def upload_file(
    request: Request,
    archivo: UploadFile = File(...),
    usuario_id: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Sube un archivo con deduplicación por hash. Devuelve su ID y numero_usos
    actual (0 si es nuevo): quien lo asocie a un recurso debe incrementarlo.

    Lo llaman el frontend (vía gateway) y los servicios (service-token). Cada
    subida queda en ``file_subida``: por gateway con el usuario de la sesión;
    un servicio que sube a nombre de un usuario lo manda en ``usuario_id``.
    """
    acceso = await verify_internal_access(request)
    subida_usuario = acceso.usuario_id if acceso.servicio == "gateway" else usuario_id

    file_data = await archivo.read()

    max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    validation_result = await validate_file_complete(
        file_data=file_data,
        filename=archivo.filename,
        max_size_mb=max_size
    )
    sanitized_filename = validation_result["sanitized_filename"]
    mime_type = validation_result["mime_type"]

    resultado_escaneo = escanear_archivo(file_data, archivo.filename)
    if not resultado_escaneo["ok"]:
        logger.error(f"Archivo rechazado por antivirus: {resultado_escaneo['mensaje']}")
        raise HTTPException(
            status_code=400,
            detail=f"Archivo rechazado: {resultado_escaneo['mensaje']}"
        )

    resultado_upload = await upload_file_with_deduplication(
        db=db,
        file_data=file_data,
        original_filename=sanitized_filename,
        content_type=mime_type,
        subida=(subida_usuario, acceso.servicio),
    )
    if not resultado_upload.get("ok"):
        raise HTTPException(
            status_code=500,
            detail=f"Error subiendo archivo: {resultado_upload.get('message', 'Error desconocido')}"
        )

    return JSONResponse(
        content={
            "ok": True,
            "file_id": resultado_upload["id"],
            "file_url": resultado_upload["url"],
            "file_hash": resultado_upload["file_hash"],
            "message": resultado_upload["message"],
            "deduplicated": resultado_upload.get("deduplicated", False),
            "numero_usos": resultado_upload.get("numero_usos", 0)
        }
    )

@router.get("/{file_id}")
async def get_file_by_id(
    request: Request,
    file_id: int,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Retorna la información de un documento por su ID unico.
    """
    exigir_acceso_directo(await verify_internal_access(request), file_id)

    stmt = select(FileHash).where(FileHash.id == file_id)
    result = await db.execute(stmt)
    file_record = result.scalar_one_or_none()

    if not file_record:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return JSONResponse(
        content={
            "ok": True,
            "data": {
                "id": file_record.id,
                "file_url": file_record.file_url,
                "content_type": file_record.content_type,
                "file_size": file_record.file_size,
                "numero_usos": file_record.numero_usos
            }
        }
    )

@router.post("/batch")
async def get_files_batch(
    request: Request,
    file_request: FilesBatchRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Retorna las URLs de múltiples documentos dados sus IDs.
    """
    verify_service_only_access(request)

    if not file_request.file_ids:
        return JSONResponse(content={"ok": True, "data": []})

    stmt = select(FileHash).where(FileHash.id.in_(file_request.file_ids))
    result = await db.execute(stmt)
    files = result.scalars().all()

    data = []
    for file_record in files:
        data.append({
            "id": file_record.id,
            "file_url": file_record.file_url,
            "content_type": file_record.content_type,
            "file_size": file_record.file_size,
            "numero_usos": file_record.numero_usos
        })

    return JSONResponse(content={"ok": True, "data": data})

@router.get("/download/{file_id}")
async def download_file_by_id(
    request: Request,
    file_id: int,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Descarga un archivo desde MinIO dado su ID, por bloques y con soporte de
    rangos (``Range``/``If-Range`` -> 206, 416 si no cabe). Solo PDF e imágenes
    se sirven ``inline``; el resto como adjunto ``application/octet-stream``.
    """
    exigir_acceso_directo(await verify_internal_access(request), file_id)

    file_record = (await db.execute(
        select(FileHash).where(FileHash.id == file_id)
    )).scalar_one_or_none()

    if not file_record:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    object_name = file_record.file_url
    try:
        tamano = file_record.file_size
        if tamano is None:
            tamano = await asyncio.to_thread(tamano_objeto, object_name)
    except S3Error:
        raise HTTPException(status_code=404, detail="Archivo no encontrado en almacenamiento")

    etag_actual = etag(file_record.file_hash)
    media_type, disposicion = tipo_y_disposicion(file_record.content_type)
    filename = object_name.rsplit("/", 1)[-1]
    headers = {
        **cabeceras_seguridad(),
        "Accept-Ranges": "bytes",
        "ETag": etag_actual,
        "Content-Disposition": f'{disposicion}; filename="{filename}"',
    }

    rango = None
    if rango_vigente(request.headers.get("if-range"), etag_actual):
        try:
            rango = parse_range(request.headers.get("range"), tamano)
        except RangoNoSatisfacible:
            return Response(status_code=416, headers={**headers, "Content-Range": f"bytes */{tamano}"})

    inicio, fin = rango if rango else (0, tamano - 1)
    longitud = fin - inicio + 1 if tamano else 0
    try:
        objeto = await asyncio.to_thread(abrir_objeto, object_name, inicio, longitud if rango else 0)
    except S3Error:
        raise HTTPException(status_code=404, detail="Archivo no encontrado en almacenamiento")

    headers["Content-Length"] = str(longitud)
    if rango:
        headers["Content-Range"] = f"bytes {inicio}-{fin}/{tamano}"
    return StreamingResponse(
        iterar_objeto(objeto),
        status_code=206 if rango else 200,
        media_type=media_type,
        headers=headers,
    )

@router.put("/increment-usage")
async def increment_file_usage(
    request: Request,
    file_request: FileStateUpdateRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Registra que un recurso usa los archivos; mientras tengan uso el cleanup
    no los borra.

    - ``file_ids`` (formato actual): suma 1 a numero_usos de cada uno.
    - ``usos`` (formato nuevo): upsert en file_uso con el servicio del token;
      numero_usos sube solo por cada asociación nueva (repetir es idempotente).
      Con ``usuario_id`` se valida que no asocie archivos ajenos (no subidos
      por él ni ya de esa entidad): según ARCHIVOS_VALIDAR_ASOCIACION se
      rechaza el lote con 403 (on) o solo se registra en el log (log).
    """
    servicio = verify_service_only_access(request)

    if file_request.usos:
        rechazados = []
        if MODO_VALIDACION in ("log", "on"):
            rechazados = await validar_asociacion(db, servicio, file_request.usos, file_request.usuario_id)
        if rechazados:
            logger.warning(
                f"Asociación de archivos ajenos ({'rechazada' if MODO_VALIDACION == 'on' else 'solo registro'}): "
                f"servicio={servicio} usuario={file_request.usuario_id} file_ids={rechazados}"
            )
            if MODO_VALIDACION == "on":
                return JSONResponse(status_code=403, content={
                    "ok": False,
                    "message": "Hay archivos que el usuario no subió ni pertenecen a esta entidad",
                    "rechazados": rechazados,
                })
        resultado = await aplicar_usos(db, servicio, file_request.usos, file_request.usuario_id)
        await db.commit()
        return JSONResponse(content={
            "ok": True,
            "message": f"Uso registrado para {resultado['registrados']} asociación(es) nueva(s)",
            **resultado,
        })

    if not file_request.file_ids:
        return JSONResponse(status_code=400, content={"ok": False, "message": "No file_ids provided."})

    files = (await db.execute(
        select(FileHash).where(FileHash.id.in_(file_request.file_ids))
    )).scalars().all()

    for file_record in files:
        file_record.numero_usos += 1

    await db.commit()

    return JSONResponse(content={"ok": True, "message": f"Uso incrementado para {len(files)} archivo(s)"})

@router.put("/decrement-usage")
async def decrement_file_usage(
    request: Request,
    file_request: FileStateUpdateRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Libera el uso al desvincular archivos de un recurso (numero_usos nunca baja
    de 0; en 0 quedan elegibles para el cleanup tras el periodo de gracia).

    - ``file_ids`` (formato actual): resta 1 a cada uno.
    - ``usos`` (formato nuevo): borra esas filas de file_uso del servicio y
      resta 1 por cada fila borrada.
    """
    servicio = verify_service_only_access(request)

    if file_request.usos:
        quitados = await quitar_usos(db, servicio, file_request.usos)
        await db.commit()
        return JSONResponse(content={
            "ok": True, "message": f"Uso liberado para {quitados} asociación(es)", "quitados": quitados,
        })

    if not file_request.file_ids:
        return JSONResponse(status_code=400, content={"ok": False, "message": "No file_ids provided."})

    files = (await db.execute(
        select(FileHash).where(FileHash.id.in_(file_request.file_ids))
    )).scalars().all()

    decremented_count = 0
    for file_record in files:
        if file_record.numero_usos > 0:
            file_record.numero_usos -= 1
            decremented_count += 1

    await db.commit()

    return JSONResponse(content={"ok": True, "message": f"Uso decrementado para {decremented_count} archivo(s)"})

@router.post("/registrar-usos")
async def registrar_usos(
    request: Request,
    body: RegistrarUsosRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Carga inicial de dueños (backfill): registra en file_uso las asociaciones
    que el servicio ya tiene, SIN tocar numero_usos (esos archivos ya fueron
    contados con el formato anterior). Idempotente; máx. 1000 por llamada.
    """
    servicio = verify_service_only_access(request)
    resultado = await aplicar_usos(db, servicio, body.usos, None, mover_contador=False)
    await db.commit()
    return JSONResponse(content={"ok": True, **resultado})

# PDF unificado: cuántas uniones a la vez por worker, desde qué tamaño el
# resultado pasa de memoria a disco y tamaño de los bloques que se envían.
_UNIONES_SIMULTANEAS = int(os.getenv("UNIFIED_PDF_CONCURRENCIA", "2"))
_UNIONES = asyncio.Semaphore(_UNIONES_SIMULTANEAS)
_SALIDA_EN_MEMORIA_MAX = 20 * 1024 * 1024
_TAMANO_BLOQUE = 256 * 1024


def _unir_pdfs(archivos: list[tuple[int, str]]) -> tuple[tempfile.SpooledTemporaryFile, int]:
    """Une los PDF en orden (corre en un hilo). Cada archivo se baja a disco y
    pypdf lo lee desde ahí, sin tenerlos todos en memoria; el resultado queda en
    un archivo temporal que pasa a disco desde ``_SALIDA_EN_MEMORIA_MAX``.

    Un archivo dañado o ausente en MinIO se omite (no aborta el PDF completo):
    si falta es porque no se anexó, y sigue el siguiente del flujo."""
    from pypdf import PdfReader, PdfWriter

    escritor = PdfWriter()
    procesados = 0
    salida = tempfile.SpooledTemporaryFile(max_size=_SALIDA_EN_MEMORIA_MAX)
    with tempfile.TemporaryDirectory(prefix="unificado-") as carpeta:
        for indice, (file_id, url) in enumerate(archivos):
            ruta = os.path.join(carpeta, f"{indice}.pdf")
            try:
                if not descargar_a_archivo(url, ruta):
                    logger.warning(f"[DOWNLOAD-UNIFIED] No se pudo descargar archivo ID {file_id}")
                    continue
                for pagina in PdfReader(ruta).pages:
                    escritor.add_page(pagina)
                procesados += 1
            except Exception as e:
                logger.warning(f"[DOWNLOAD-UNIFIED] Error procesando archivo ID {file_id}: {e}")
        if procesados:
            escritor.write(salida)
            salida.seek(0)
        escritor.close()
    return salida, procesados


@router.post("/download-unified")
async def download_unified_pdf(
    request: Request,
    file_request: FilesBatchRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Combina varios archivos en un único PDF, en el orden de file_ids.
    """
    verify_service_only_access(request)

    if not file_request.file_ids:
        raise HTTPException(status_code=400, detail="No se proporcionaron IDs de archivos")

    result = await db.execute(select(FileHash).where(FileHash.id.in_(file_request.file_ids)))
    files_dict = {f.id: f for f in result.scalars().all()}

    # Mantener el orden solicitado en file_ids (el consumidor decide el orden del PDF).
    files_ordered = []
    for file_id in file_request.file_ids:
        if file_id in files_dict:
            files_ordered.append(files_dict[file_id])
        else:
            logger.warning(f"[DOWNLOAD-UNIFIED] Archivo {file_id} no encontrado en BD")

    if not files_ordered:
        raise HTTPException(status_code=404, detail="No se encontraron archivos válidos")

    # Como mucho _UNIONES_SIMULTANEAS uniones a la vez por worker; la unión
    # (MinIO + pypdf) corre en un hilo para no bloquear el event loop.
    async with _UNIONES:
        salida, procesados = await asyncio.to_thread(
            _unir_pdfs, [(f.id, f.file_url) for f in files_ordered]
        )
    if procesados == 0:
        salida.close()
        raise HTTPException(status_code=500, detail="No se pudo procesar ningún documento")

    def _contenido():
        try:
            while bloque := salida.read(_TAMANO_BLOQUE):
                yield bloque
        finally:
            salida.close()

    return StreamingResponse(
        _contenido(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="documentos_unificados.pdf"'}
    )
