"""/revision-documentos — proceso de revisión de los documentos de cada etapa
(plan §5, DISENO_TECNICO §4). Equivalente a ``/revision-informes`` de
infraction: mismo contrato ``ProcesoDetalle`` y mismos campos multipart para
que ``@features/proceso-revision`` funcione con un adapter de endpoints.

La versión firmada NO se sube aquí: la carga cada etapa con "Cargar versión
final" (``services.revision_documentos.cargar_version_final``), que en la misma
transacción crea el acto administrativo o llena el concepto.

Bloqueos: expediente → proceso (mismo orden que las etapas), ``FOR UPDATE``.
"""
from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from datetime import datetime
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from satc_shared.clients import NotFoundError, ServiceClientError
from satc_shared.review_process import (
    PermisoDenegado,
    ProcesoDetalle,
    ProcesoNoEncontrado,
    ReviewError,
    RevisorInfo,
)

from core.acceso import usuario_actual
from core.permission import Permission
from db.deps import get_db_managed
from db.models.documento_proceso import (
    DocumentoProceso,
    DocumentoProcesoRevision,
    DocumentoProcesoVersion,
)
from services.concurrencia import bloquear_expediente
import services.docs as docs_svc
import services.users as users_svc
from services.revision_documentos import (
    APROBADO_FIRMA,
    EN_REVISION,
    FLUJO,
    MOTIVO_VERSION_FINAL,
    Avisos,
    Conflicto,
    avisos_tras_revision,
    avisos_tras_version,
    cadena_de,
    datos_expediente,
    etiqueta_etapa,
    etiqueta_permiso,
    etiqueta_tipo_documento,
    http_error,
    permisos_de_usuario,
    proceso_vigente,
    servicio,
    subir_a_docs,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════ contrato

class PermisoPasoInfo(BaseModel):
    permiso: str
    etiqueta: str
    revisado: bool
    revisor_id: Optional[int] = None
    revisor_nombre: Optional[str] = None
    accion: Optional[str] = None
    fecha_revision: Optional[datetime] = None


class PasoInfo(BaseModel):
    numero: int  # 1-based
    estado: str  # completado | actual | pendiente
    permisos: list[PermisoPasoInfo]


class ProcesoDocumentoDetalle(ProcesoDetalle):
    """``ProcesoDetalle`` (contrato genérico) + datos del documento de la etapa."""

    expediente_id: int
    expediente_radicado: Optional[str] = None
    expediente_codigo: Optional[str] = None
    tipo_documento: str
    tipo_documento_etiqueta: str
    etapa_tipo: str
    etapa_etiqueta: str
    etapa_ref_id: int
    activo: bool
    encargado_id: int
    encargado_nombre: Optional[str] = None
    paso_actual: int  # 1-based
    total_pasos: int
    pasos: list[PasoInfo]


# ═══════════════════════════════════════════════════════════════ helpers

async def _user_id(request: Request) -> int:
    return (await usuario_actual(request)).user_id


async def _detalle(db: AsyncSession, proceso_id: int, user_id: int) -> dict:
    svc = servicio()
    try:
        ctx = await svc.contexto(db, proceso_id)
        if not await FLUJO.puede_ver(ctx, user_id):
            raise PermisoDenegado("Sin acceso")
    except (ProcesoNoEncontrado, PermisoDenegado):
        # 403 en ambos casos: no revelar qué ids existen.
        raise HTTPException(status_code=403, detail="No tienes acceso a este documento")
    p: DocumentoProceso = ctx.proceso
    cadena = cadena_de(p.tipo_documento)

    revisiones = (await db.execute(
        select(DocumentoProcesoRevision)
        .where(DocumentoProcesoRevision.proceso_id == p.id)
        .order_by(DocumentoProcesoRevision.fecha_revision, DocumentoProcesoRevision.id)
    )).scalars().all()
    pendientes = await FLUJO.pendientes_paso(ctx) if p.estado == EN_REVISION else []

    # Usuarios con los permisos pendientes del paso actual (cache de services.users).
    titulares: dict[int, str | None] = {}
    for permiso in pendientes:
        for uid, info in (await users_svc.get_users_by_permission(permiso) or {}).items():
            titulares.setdefault(int(uid), (info or {}).get("nombre"))

    ids = {p.creador_id, *(r.revisor_id for r in revisiones), *titulares}
    usuarios = await users_svc.get_user_info(sorted(ids))
    nombres = {uid: (info or {}).get("nombre") for uid, info in usuarios.items() if (info or {}).get("nombre")}
    for uid, nombre in titulares.items():
        if nombre and uid not in nombres:
            nombres[uid] = nombre

    detalle = await svc.detalle(db, proceso_id, user_id=user_id, nombres_usuarios=nombres, verificar_acceso=False)

    # Pasos: quién revisó cada permiso de cada paso (primera revisión con él).
    primera: dict[tuple[int, str], DocumentoProcesoRevision] = {}
    for r in revisiones:
        if r.paso is not None and r.permiso:
            primera.setdefault((r.paso, r.permiso), r)
    paso_actual = p.paso_actual or 0
    pasos = []
    for i, permisos in enumerate(cadena.pasos):
        if i < paso_actual or (i == paso_actual and p.estado not in ("pendiente_carga", EN_REVISION, "rechazado")):
            estado_paso = "completado"
        elif i == paso_actual:
            estado_paso = "actual"
        else:
            estado_paso = "pendiente"
        items = []
        for permiso in permisos:
            r = primera.get((i, permiso))
            items.append(PermisoPasoInfo(
                permiso=permiso, etiqueta=etiqueta_permiso(permiso), revisado=r is not None,
                revisor_id=r.revisor_id if r else None,
                revisor_nombre=nombres.get(r.revisor_id) if r else None,
                accion=r.accion if r else None,
                fecha_revision=r.fecha_revision if r else None,
            ))
        pasos.append(PasoInfo(numero=i + 1, estado=estado_paso, permisos=items))

    # "revisores": quienes ya revisaron + titulares de los permisos pendientes.
    revisores: dict[int, RevisorInfo] = {}
    for r in revisiones:
        revisores.setdefault(r.revisor_id, RevisorInfo(
            revisor_id=r.revisor_id, nombre=nombres.get(r.revisor_id), fecha_asignacion=r.fecha_revision,
        ))
    for uid in titulares:
        revisores.setdefault(uid, RevisorInfo(revisor_id=uid, nombre=nombres.get(uid)))

    radicado, codigo = await datos_expediente(db, p.expediente_id)
    datos = detalle.model_dump()
    datos["revisores"] = [r.model_dump() for r in revisores.values()]
    salida = ProcesoDocumentoDetalle(
        **datos,
        expediente_id=p.expediente_id,
        expediente_radicado=radicado,
        expediente_codigo=codigo,
        tipo_documento=p.tipo_documento,
        tipo_documento_etiqueta=etiqueta_tipo_documento(p.tipo_documento),
        etapa_tipo=p.etapa_tipo,
        etapa_etiqueta=etiqueta_etapa(p.etapa_tipo),
        etapa_ref_id=p.etapa_ref_id,
        activo=bool(p.activo),
        encargado_id=p.creador_id,
        encargado_nombre=nombres.get(p.creador_id),
        paso_actual=paso_actual + 1,
        total_pasos=len(cadena.pasos),
        pasos=pasos,
    ).model_dump(mode="json")
    # Agente C: etapa del plan a la que pertenece (etapa_padre, etapa_padre_etiqueta, sub_proceso).
    from services.etapas import etapas_padre

    salida.update((await etapas_padre(db, [p]))[p.id])
    # Extra no tipado en el contrato genérico: paso/permiso de cada revisión.
    por_id = {r.id: r for r in revisiones}
    for item in salida["revisiones"]:
        r = por_id.get(item["revision_id"])
        item["paso"] = (r.paso + 1) if r is not None and r.paso is not None else None
        item["permiso"] = r.permiso if r is not None else None
        item["permiso_etiqueta"] = etiqueta_permiso(r.permiso) if r is not None and r.permiso else None
    return salida


async def _bloquear(db: AsyncSession, proceso_id: int) -> None:
    """Bloquea el expediente ANTES que el proceso (mismo orden que las etapas)."""
    expediente_id = await db.scalar(select(DocumentoProceso.expediente_id).where(DocumentoProceso.id == proceso_id))
    if expediente_id is None:
        raise HTTPException(status_code=403, detail="No tienes acceso a este documento")
    await bloquear_expediente(db, expediente_id)


async def _verificar_acceso(db: AsyncSession, proceso_id: int, user_id: int) -> None:
    try:
        ctx = await servicio().contexto(db, proceso_id)
        if await FLUJO.puede_ver(ctx, user_id):
            return
    except ProcesoNoEncontrado:
        pass
    raise HTTPException(status_code=403, detail="No tienes acceso a este documento")


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


# ═══════════════════════════════════════════════════════════════ detalle

@router.get("/por-etapa/{etapa_tipo}/{etapa_ref_id}", status_code=200)
async def detalle_por_etapa(
    request: Request, etapa_tipo: str, etapa_ref_id: int, db: AsyncSession = Depends(get_db_managed)
):
    """Proceso vigente de una fila de etapa (``etapa_tipo`` = tabla)."""
    user_id = await _user_id(request)
    proceso = await proceso_vigente(db, etapa_tipo, etapa_ref_id)
    if proceso is None:
        lectura = await permisos_de_usuario(
            user_id, (Permission.CONSULT, Permission.MANAGE, Permission.SUPER_MANAGE, *Permission.REVISORES)
        )
        if not lectura:
            raise HTTPException(status_code=403, detail="No tienes acceso a este documento")
        return JSONResponse(status_code=404, content={
            "ok": False, "detail": "La etapa no tiene un proceso de revisión vigente",
        })
    return JSONResponse(content=await _detalle(db, proceso.id, user_id))


@router.get("/{proceso_id}", status_code=200)
async def detalle_proceso(request: Request, proceso_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = await _user_id(request)
    return JSONResponse(content=await _detalle(db, proceso_id, user_id))


@router.get("/{proceso_id}/historial", status_code=200)
async def historial_proceso(request: Request, proceso_id: int, db: AsyncSession = Depends(get_db_managed)):
    """Versiones y revisiones (más reciente primero)."""
    user_id = await _user_id(request)
    d = await _detalle(db, proceso_id, user_id)
    return JSONResponse(content={"ok": True, "data": {"versiones": d["versiones"], "revisiones": d["revisiones"]}})


@router.get("/{proceso_id}/auditoria", status_code=200)
async def auditoria_proceso(request: Request, proceso_id: int, db: AsyncSession = Depends(get_db_managed)):
    """Auditoría del proceso (cronológica)."""
    user_id = await _user_id(request)
    d = await _detalle(db, proceso_id, user_id)
    return JSONResponse(content={"ok": True, "data": d["auditoria"]})


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
    """``aprobado`` | ``aprobado_firma`` | ``devuelto`` (comentario obligatorio,
    adjunto opcional pdf/doc/docx). Se revisa con el primer permiso pendiente del
    paso actual que tenga el usuario."""
    user_id = await _user_id(request)
    svc = servicio()
    tiene_adjunto = adjunto is not None and bool(adjunto.filename)

    try:
        await _bloquear(db, proceso_id)
        ctx = await svc.contexto(db, proceso_id, para_actualizar=True)
        acc = FLUJO.acciones.get(accion)
        ref = None
        if tiene_adjunto:
            # Validar ANTES de subir para no dejar huérfanos en app-docs.
            if not await FLUJO.permisos_usuario(ctx, user_id):
                raise PermisoDenegado("No tienes un permiso de revisor para este documento")
            if not await FLUJO.puede_revisar(ctx, user_id):
                raise Conflicto("No puedes revisar este documento ahora. Recarga")
            if acc is None or not acc.admite_adjunto:
                raise HTTPException(status_code=400, detail="Solo se puede adjuntar un archivo al devolver")
            if not adjunto.filename.lower().endswith(acc.adjunto_extensiones):
                raise HTTPException(
                    status_code=400,
                    detail=f"Formato no permitido. Permitidos: {', '.join(acc.adjunto_extensiones)}",
                )
            ref = await subir_a_docs(adjunto)

        res = await svc.revisar(db, proceso_id, user_id=user_id, accion=accion, comentario=comentario, adjunto=ref)
        proceso: DocumentoProceso = res.proceso
        avisos = Avisos()
        await avisos_tras_revision(db, avisos, res)
        await db.commit()
    except ReviewError as e:
        await db.rollback()
        raise http_error(e)
    except HTTPException:
        await db.rollback()
        raise

    await avisos.enviar()
    return JSONResponse(content={
        "ok": True,
        "proceso_id": proceso.id,
        "accion": res.revision.accion,
        "permiso": res.permiso,
        "estado": FLUJO.estado_info(res.estado_nuevo).model_dump(),
        "paso_actual": (proceso.paso_actual or 0) + 1,
        "avanzo_paso": res.avanzo_paso,
        "numero_devoluciones": proceso.numero_devoluciones,
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
    """El encargado sube la primera versión (``pendiente_carga``) o una corrección
    (``rechazado``). La versión firmada (``aprobado_firma``) se carga desde la etapa."""
    user_id = await _user_id(request)
    svc = servicio()

    try:
        await _bloquear(db, proceso_id)
        ctx = await svc.contexto(db, proceso_id, para_actualizar=True)
        p: DocumentoProceso = ctx.proceso
        if not await FLUJO.puede_subir_version(ctx, user_id):
            raise PermisoDenegado("Solo el encargado puede subir versiones de este documento")
        if not p.activo:
            raise Conflicto("Este proceso de revisión ya no está vigente. Recarga")
        if p.estado == APROBADO_FIRMA:
            raise Conflicto(MOTIVO_VERSION_FINAL)
        if not FLUJO.subida_permitida_en(p):
            raise Conflicto(
                f"En el estado actual ({FLUJO.estado_info(p.estado).etiqueta}) no se puede subir una nueva versión"
            )
        extensiones = FLUJO.extensiones_subida(p)
        if not (archivo.filename or "").lower().endswith(tuple(extensiones)):
            raise HTTPException(status_code=400, detail=f"Formato no permitido. Permitidos: {', '.join(extensiones)}")
        ref = await subir_a_docs(archivo)

        res = await svc.subir_version(db, proceso_id, user_id=user_id, archivo=ref, comentario=comentario)
        proceso: DocumentoProceso = res.proceso
        avisos = Avisos()
        await avisos_tras_version(db, avisos, res)
        await db.commit()
    except ReviewError as e:
        await db.rollback()
        raise http_error(e)
    except HTTPException:
        await db.rollback()
        raise

    await avisos.enviar()
    return JSONResponse(content={
        "ok": True,
        "proceso_id": proceso.id,
        "version": res.version.numero_version,
        "version_id": res.version.id,
        "estado": FLUJO.estado_info(res.estado_nuevo).model_dump(),
        "paso_actual": (proceso.paso_actual or 0) + 1,
        "message": "Versión subida exitosamente",
    })


# ═══════════════════════════════════════════════════════════════ descargas

@router.get("/{proceso_id}/versiones/{version_id}/descarga")
async def descargar_version(
    request: Request, proceso_id: int, version_id: int, db: AsyncSession = Depends(get_db_managed)
):
    user_id = await _user_id(request)
    await _verificar_acceso(db, proceso_id, user_id)
    version = await db.scalar(select(DocumentoProcesoVersion).where(
        DocumentoProcesoVersion.id == version_id, DocumentoProcesoVersion.proceso_id == proceso_id
    ))
    if version is None:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    return await _stream_archivo(version.file_id, version.archivo_nombre)


@router.get("/{proceso_id}/revisiones/{revision_id}/adjunto")
async def descargar_adjunto(
    request: Request, proceso_id: int, revision_id: int, db: AsyncSession = Depends(get_db_managed)
):
    user_id = await _user_id(request)
    await _verificar_acceso(db, proceso_id, user_id)
    revision = await db.scalar(select(DocumentoProcesoRevision).where(
        DocumentoProcesoRevision.id == revision_id, DocumentoProcesoRevision.proceso_id == proceso_id
    ))
    if revision is None or not revision.adjunto_url:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    return await _stream_archivo(revision.adjunto_file_id, revision.adjunto_nombre or "adjunto")
