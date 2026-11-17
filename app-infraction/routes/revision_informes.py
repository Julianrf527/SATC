"""/revision-informes — proceso de revisión propio del informe técnico.

Reemplaza el flujo que vivía en app-docs (documentos con origen
'informe_tecnico' + sincronización). Todo ocurre en infracciones_db y en una
sola transacción: la revisión/subida que aprueba el proceso también acepta el
informe técnico. Los archivos se suben a app-docs (/files/upload, que valida y
pasa ClamAV) con FilesClient y aquí solo se guarda la referencia.
"""
from __future__ import annotations

import json
import logging
from contextlib import AsyncExitStack
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from satc_shared.clients import NotFoundError, ServiceClientError
from satc_shared.review_process import (
    APROBADO,
    ArchivoRef,
    PermisoDenegado,
    ProcesoDetalle,
    ProcesoNoEncontrado,
    ReviewError,
)

from core.permission import Permission
from db.deps import get_db_managed
from db.models.expediente import Expediente
from db.models.informe_proceso import (
    InformeProceso,
    InformeProcesoRevision,
    InformeProcesoRevisor,
    InformeProcesoVersion,
)
from db.models.informe_tecnico import InformeTecnico
from utils.verify_token import verify_gateway_token
import services.docs as docs_svc
import services.users as users_svc
from services.revision_informes import (
    FLUJO,
    Avisos,
    aplicar_aprobacion,
    avisos_revision,
    avisos_version,
    contexto_informe,
    proceso_vigente,
    servicio,
)

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_BYTES_ARCHIVO = 50 * 1024 * 1024  # tope defensivo; app-docs aplica su propio límite (MAX_FILE_SIZE_MB)


class ProcesoInformeDetalle(ProcesoDetalle):
    """``ProcesoDetalle`` (contrato genérico) + datos del informe técnico."""

    informe_id: int
    expediente_id: int
    expediente_radicado: Optional[str] = None
    tipo_informe: Optional[str] = None
    modo: Optional[str] = None
    activo: bool
    profesional_nombre: Optional[str] = None
    asignador_id: Optional[int] = None


# ═══════════════════════════════════════════════════════════════ helpers

def _http(e: ReviewError) -> HTTPException:
    return HTTPException(status_code=e.status_code, detail=e.detail)


async def _detalle(db: AsyncSession, proceso_id: int, user_id: int) -> dict:
    svc = servicio()
    try:
        ctx = await svc.contexto(db, proceso_id)
        if not await FLUJO.puede_ver(ctx, user_id):
            raise PermisoDenegado("Sin acceso")
    except (ProcesoNoEncontrado, PermisoDenegado):
        # 403 en ambos casos: no revelar qué ids existen.
        raise HTTPException(status_code=403, detail="No tienes acceso a este proceso")
    proceso: InformeProceso = ctx.proceso

    ids = {proceso.creador_id}
    if proceso.asignador_id:
        ids.add(proceso.asignador_id)
    ids.update(await ctx.revisores_ids())
    ids.update(r for (r,) in (await db.execute(
        select(InformeProcesoRevision.revisor_id).where(InformeProcesoRevision.proceso_id == proceso.id).distinct()
    )).all())
    usuarios = await users_svc.get_user_info(sorted(ids))
    nombres = {uid: (info or {}).get("nombre") for uid, info in usuarios.items() if (info or {}).get("nombre")}

    detalle = await svc.detalle(db, proceso_id, user_id=user_id, nombres_usuarios=nombres, verificar_acceso=False)
    informe = await db.scalar(select(InformeTecnico).where(InformeTecnico.id == proceso.informe_id))
    radicado = await db.scalar(select(Expediente.radicado).where(Expediente.id == informe.expediente_id))
    return ProcesoInformeDetalle(
        **detalle.model_dump(),
        informe_id=informe.id,
        expediente_id=informe.expediente_id,
        expediente_radicado=radicado,
        tipo_informe=informe.tipo_informe,
        modo=informe.modo,
        activo=bool(proceso.activo),
        profesional_nombre=nombres.get(proceso.creador_id),
        asignador_id=proceso.asignador_id,
    ).model_dump(mode="json")


async def _subir_a_docs(archivo: UploadFile) -> ArchivoRef:
    nombre = (archivo.filename or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="Archivo sin nombre")
    data = await archivo.read()
    if not data:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(data) > MAX_BYTES_ARCHIVO:
        raise HTTPException(status_code=413, detail="El archivo supera el tamaño máximo permitido (50 MB)")
    try:
        subido = await docs_svc.files_client.upload(nombre, data, archivo.content_type or "application/octet-stream")
    except ServiceClientError as e:
        if e.status_code and 400 <= e.status_code < 500 and e.status_code not in (401, 403):
            detalle = e.body
            try:
                detalle = json.loads(e.body).get("detail") or e.body
            except (ValueError, AttributeError, TypeError):
                pass
            raise HTTPException(status_code=400, detail=f"El archivo fue rechazado: {detalle}")
        logger.error(f"Error subiendo archivo a app-docs: {e}")
        raise HTTPException(status_code=502, detail="No se pudo subir el archivo")
    return ArchivoRef(file_id=subido.file_id, url=subido.file_url, nombre=nombre, size=len(data))


def _content_disposition(nombre: str) -> str:
    ascii_ = nombre.encode("ascii", "ignore").decode() or "archivo"
    ascii_ = ascii_.replace('"', "")
    return f"attachment; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nombre)}"


async def _stream_archivo(file_id: Optional[int], nombre: str) -> StreamingResponse:
    if not file_id:
        raise HTTPException(status_code=404, detail="El archivo no está disponible")
    stack = AsyncExitStack()
    try:
        resp = await stack.enter_async_context(docs_svc.files_client.download(file_id))
    except NotFoundError:
        await stack.aclose()
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    except ServiceClientError as e:
        await stack.aclose()
        logger.error(f"Error descargando archivo {file_id}: {e}")
        raise HTTPException(status_code=502, detail="No se pudo descargar el archivo")

    async def _cuerpo():
        try:
            async for chunk in resp.aiter_bytes():
                yield chunk
        finally:
            await stack.aclose()

    return StreamingResponse(
        _cuerpo(),
        media_type=resp.headers.get("content-type", "application/octet-stream"),
        headers={"Content-Disposition": _content_disposition(nombre)},
    )


async def _verificar_acceso(db: AsyncSession, proceso_id: int, user_id: int) -> None:
    try:
        ctx = await servicio().contexto(db, proceso_id)
        if await FLUJO.puede_ver(ctx, user_id):
            return
    except ProcesoNoEncontrado:
        pass
    raise HTTPException(status_code=403, detail="No tienes acceso a este proceso")


async def _bloquear_informe(db: AsyncSession, proceso_id: int) -> None:
    """Bloquea el informe ANTES que el proceso: mismo orden que /informes
    (asignar, reasignar, cambiar-modo), para no cruzar bloqueos."""
    informe_id = await db.scalar(select(InformeProceso.informe_id).where(InformeProceso.id == proceso_id))
    if informe_id is not None:
        await db.execute(select(InformeTecnico.id).where(InformeTecnico.id == informe_id).with_for_update())


async def _revisores(db: AsyncSession, proceso_id: int) -> list[int]:
    return [r for (r,) in (await db.execute(
        select(InformeProcesoRevisor.revisor_id).where(InformeProcesoRevisor.proceso_id == proceso_id)
    )).all()]


# ═══════════════════════════════════════════════════════════════ detalle

@router.get("/por-informe/{informe_id}", status_code=200)
async def detalle_por_informe(request: Request, informe_id: int, db: AsyncSession = Depends(get_db_managed)):
    """Proceso vigente del informe (reemplaza GET /informes/{id}/doc-process)."""
    user_id = int(verify_gateway_token(request)["user_id"])
    proceso = await proceso_vigente(db, informe_id)
    if proceso is None:
        informe = await db.scalar(select(InformeTecnico).where(InformeTecnico.id == informe_id))
        es_involucrado = informe is not None and user_id in (
            informe.profesional_asignado_id, informe.revisor_asignado_id
        )
        if not es_involucrado and not await users_svc.verify_permission(user_id, Permission.ASSIGN_REPORTS):
            raise HTTPException(status_code=403, detail="No tienes acceso a este informe")
        return JSONResponse(status_code=404, content={"ok": False, "detail": "El informe no tiene un proceso de revisión vigente"})
    return JSONResponse(content=await _detalle(db, proceso.id, user_id))


@router.get("/{proceso_id}", status_code=200)
async def detalle_proceso(request: Request, proceso_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = int(verify_gateway_token(request)["user_id"])
    return JSONResponse(content=await _detalle(db, proceso_id, user_id))


# ═══════════════════════════════════════════════════════════════ revisar

@router.post("/{proceso_id}/revisiones", status_code=200)
async def revisar_proceso(
    request: Request,
    proceso_id: int,
    accion: str = Form(...),
    comentario: Optional[str] = Form(None),
    adjunto: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db_managed),
):
    """Acción del revisor asignado: ``aprobado`` | ``aprobado_firma`` | ``devuelto``
    (solo ``devuelto`` admite adjunto pdf/doc/docx)."""
    user_id = int(verify_gateway_token(request)["user_id"])
    svc = servicio()
    tiene_adjunto = adjunto is not None and bool(adjunto.filename)

    try:
        await _bloquear_informe(db, proceso_id)
        ctx = await svc.contexto(db, proceso_id, para_actualizar=True)
        if not await FLUJO.puede_revisar(ctx, user_id):
            raise PermisoDenegado("No estás asignado como revisor de este informe")
        acc = FLUJO.acciones.get(accion)
        if acc is None:
            raise HTTPException(status_code=400, detail=f"Acción de revisión inválida: {accion}")
        ref = None
        if tiene_adjunto:
            # Validar antes de subir para no dejar archivos huérfanos en app-docs.
            if not acc.admite_adjunto:
                raise HTTPException(status_code=400, detail="Solo se puede adjuntar un archivo al devolver")
            if not adjunto.filename.lower().endswith(acc.adjunto_extensiones):
                raise HTTPException(
                    status_code=400,
                    detail=f"Formato no permitido. Permitidos: {', '.join(acc.adjunto_extensiones)}",
                )
            ref = await _subir_a_docs(adjunto)

        res = await svc.revisar(db, proceso_id, user_id=user_id, accion=accion, comentario=comentario, adjunto=ref)
        proceso: InformeProceso = res.proceso
        _, radicado = await contexto_informe(db, proceso.informe_id)
        avisos = Avisos(proceso.informe_id)
        informe_aceptado = False
        if res.estado_nuevo == APROBADO:
            await aplicar_aprobacion(db, proceso, avisos, radicado)
            informe_aceptado = True
        avisos_revision(avisos, proceso, accion, res.estado_nuevo, radicado, ref is not None, await _revisores(db, proceso.id))
        await db.commit()
    except ReviewError as e:
        await db.rollback()
        raise _http(e)
    except HTTPException:
        await db.rollback()
        raise

    await avisos.enviar()
    return JSONResponse(content={
        "ok": True,
        "proceso_id": proceso.id,
        "informe_id": proceso.informe_id,
        "estado": FLUJO.estado_info(res.estado_nuevo).model_dump(),
        "numero_devoluciones": proceso.numero_devoluciones,
        "informe_aceptado": informe_aceptado,
        "message": res.descripcion,
    })


# ══════════════════════════════════════════════════════════ subir versión

@router.post("/{proceso_id}/versiones", status_code=200)
async def subir_version(
    request: Request,
    proceso_id: int,
    archivo: UploadFile = File(...),
    comentario: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db_managed),
):
    """El profesional asignado sube la primera versión (``pendiente_carga``),
    una corrección (``rechazado``) o la versión firmada en PDF
    (``aprobado_firma``), que se auto-aprueba y acepta el informe."""
    user_id = int(verify_gateway_token(request)["user_id"])
    svc = servicio()

    try:
        await _bloquear_informe(db, proceso_id)
        ctx = await svc.contexto(db, proceso_id, para_actualizar=True)
        if not await FLUJO.puede_subir_version(ctx, user_id):
            raise PermisoDenegado("No eres el profesional asignado a este informe")
        if not FLUJO.subida_permitida_en(ctx.proceso):
            raise HTTPException(status_code=400, detail="En el estado actual no se puede subir una nueva versión")
        extensiones = FLUJO.extensiones_subida(ctx.proceso)
        if not (archivo.filename or "").lower().endswith(tuple(extensiones)):
            raise HTTPException(status_code=400, detail=f"Formato no permitido. Permitidos: {', '.join(extensiones)}")
        ref = await _subir_a_docs(archivo)

        res = await svc.subir_version(db, proceso_id, user_id=user_id, archivo=ref, comentario=comentario)
        proceso: InformeProceso = res.proceso
        _, radicado = await contexto_informe(db, proceso.informe_id)
        avisos = Avisos(proceso.informe_id)
        informe_aceptado = False
        if res.estado_nuevo == APROBADO:
            await aplicar_aprobacion(db, proceso, avisos, radicado)
            informe_aceptado = True
        avisos_version(avisos, proceso, res.version.numero_version, res.estado_nuevo, radicado, await _revisores(db, proceso.id))
        await db.commit()
    except ReviewError as e:
        await db.rollback()
        raise _http(e)
    except HTTPException:
        await db.rollback()
        raise

    await avisos.enviar()
    return JSONResponse(content={
        "ok": True,
        "proceso_id": proceso.id,
        "informe_id": proceso.informe_id,
        "version": res.version.numero_version,
        "version_id": res.version.id,
        "estado": FLUJO.estado_info(res.estado_nuevo).model_dump(),
        "auto_aprobado": res.estado_nuevo == APROBADO,
        "informe_aceptado": informe_aceptado,
        "message": "Versión firmada cargada: informe aprobado" if informe_aceptado else "Versión subida exitosamente",
    })


# ═══════════════════════════════════════════════════════════════ descargas

@router.get("/{proceso_id}/versiones/{version_id}/descarga")
async def descargar_version(
    request: Request, proceso_id: int, version_id: int, db: AsyncSession = Depends(get_db_managed)
):
    user_id = int(verify_gateway_token(request)["user_id"])
    await _verificar_acceso(db, proceso_id, user_id)
    version = await db.scalar(select(InformeProcesoVersion).where(
        InformeProcesoVersion.id == version_id, InformeProcesoVersion.proceso_id == proceso_id
    ))
    if version is None:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    return await _stream_archivo(version.file_id, version.archivo_nombre)


@router.get("/{proceso_id}/revisiones/{revision_id}/adjunto")
async def descargar_adjunto(
    request: Request, proceso_id: int, revision_id: int, db: AsyncSession = Depends(get_db_managed)
):
    user_id = int(verify_gateway_token(request)["user_id"])
    await _verificar_acceso(db, proceso_id, user_id)
    revision = await db.scalar(select(InformeProcesoRevision).where(
        InformeProcesoRevision.id == revision_id, InformeProcesoRevision.proceso_id == proceso_id
    ))
    if revision is None or not revision.adjunto_url:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    return await _stream_archivo(revision.adjunto_file_id, revision.adjunto_nombre or "adjunto")
