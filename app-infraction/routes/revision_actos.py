"""/revision-actos — proceso de revisión de los actos administrativos de
infracciones (medida preventiva, acoger concepto, cierre).

El encargado ACTUAL del expediente proyecta el acto y sube las correcciones;
cualquier usuario con ``infraccion_lider_proyecto`` lo aprueba para firma o lo
devuelve. En ``aprobado_firma`` el encargado carga la versión firmada (PDF) con
tipo, numerado y fecha: en la misma transacción se crea el acto y se enlaza a
la etapa. Reglas completas en services/revision_actos.py.

Orden de bloqueos: fila de etapa → proceso (igual que el cargue directo de
super gestión en routes/acto_admin.py).
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from satc_shared.review_process import (
    APROBADO,
    FINALIZADO,
    PermisoDenegado,
    ProcesoDetalle,
    ProcesoNoEncontrado,
    ReviewError,
    RevisorInfo,
)

from core.permission import Permission
from db.deps import get_db_managed
from db.models.documento_proceso import (
    ETAPAS_ACTO,
    DocumentoProceso,
    DocumentoProcesoRevision,
    DocumentoProcesoVersion,
)
from routes.revision_informes import _http, _stream_archivo, _subir_a_docs
from services.revision_actos import (
    APROBADO_FIRMA,
    EXTENSION_PDF,
    FLUJO,
    MOTIVO_VERSION_FINAL,
    Avisos,
    EtapaActo,
    avisos_tras_revision,
    avisos_tras_version,
    cargar_etapa,
    cargar_version_final,
    crear_acto,
    iniciar,
    proceso_vigente,
    proyectar,
    servicio,
    validar_datos_acto,
    validar_numerado_disponible,
)
from utils.log import insert_log
from utils.verify_token import verify_gateway_token
import services.users as users_svc

router = APIRouter()
logger = logging.getLogger(__name__)


ETIQUETA_LIDER_PROYECTO = "Líder de proyecto"


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


class ProcesoActoDetalle(ProcesoDetalle):
    """``ProcesoDetalle`` (contrato genérico) + datos del acto y su etapa."""

    etapa_tipo: str
    etapa_ref_id: int
    tipo_documento: str
    expediente_id: int
    expediente_radicado: Optional[str] = None
    activo: bool
    encargado_id: Optional[int] = None
    encargado_nombre: Optional[str] = None
    acto_id: Optional[int] = None
    # El usuario es el encargado y el proceso está aprobado para firma.
    puede_cargar_version_final: bool = False
    # Cadena de revisión (como recurso): un solo paso, el líder de proyecto.
    paso_actual: int = 1
    total_pasos: int = 1
    pasos: list[PasoInfo] = []


def _pasos(estado: str, revisiones) -> list[PasoInfo]:
    """Paso único del líder de proyecto. Revisado = aprobado para firma en el
    ciclo vigente (una devolución lo vuelve a dejar pendiente)."""
    aprobado = estado in (APROBADO_FIRMA, APROBADO) or (
        estado == FINALIZADO and any(r.accion == APROBADO_FIRMA for r in revisiones)
    )
    # `revisiones` viene del más reciente al más antiguo.
    ultima = next((r for r in revisiones if r.accion == APROBADO_FIRMA), None) if aprobado else None
    return [PasoInfo(
        numero=1,
        estado="completado" if aprobado else "actual",
        permisos=[PermisoPasoInfo(
            permiso=Permission.LIDER_PROYECTO,
            etiqueta=ETIQUETA_LIDER_PROYECTO,
            revisado=ultima is not None,
            revisor_id=ultima.revisor_id if ultima else None,
            revisor_nombre=ultima.revisor_nombre if ultima else None,
            accion=ultima.accion if ultima else None,
            fecha_revision=ultima.fecha_revision if ultima else None,
        )],
    )]


# ═══════════════════════════════════════════════════════════════ helpers

async def _puede_ver_etapa(user_id: int, etapa: EtapaActo) -> bool:
    if user_id == etapa.encargado_id:
        return True
    for permiso in (Permission.LIDER_PROYECTO, Permission.FILE_CONSULT, Permission.MANUAL_UPLOAD):
        if await users_svc.verify_permission(user_id, permiso):
            return True
    return False


async def _contexto_visible(db: AsyncSession, proceso_id: int, user_id: int):
    try:
        ctx = await servicio().contexto(db, proceso_id)
        if await FLUJO.puede_ver(ctx, user_id):
            return ctx
    except ProcesoNoEncontrado:
        pass
    # 403 en ambos casos: no revelar qué ids existen.
    raise HTTPException(status_code=403, detail="No tienes acceso a este proceso")


async def _detalle(db: AsyncSession, proceso_id: int, user_id: int) -> dict:
    ctx = await _contexto_visible(db, proceso_id, user_id)
    proceso: DocumentoProceso = ctx.proceso
    etapa = await cargar_etapa(db, proceso.etapa_tipo, proceso.etapa_ref_id)

    ids = {proceso.creador_id}
    if etapa.encargado_id:
        ids.add(etapa.encargado_id)
    ids.update(r for (r,) in (await db.execute(
        select(DocumentoProcesoRevision.revisor_id).where(DocumentoProcesoRevision.proceso_id == proceso.id).distinct()
    )).all())
    usuarios = await users_svc.get_user_info(sorted(ids))
    nombres = {uid: (info or {}).get("nombre") for uid, info in usuarios.items() if (info or {}).get("nombre")}

    detalle = await servicio().detalle(db, proceso_id, user_id=user_id, nombres_usuarios=nombres, verificar_acceso=False)
    # Los actos no tienen revisores asignados: revisa cualquier líder de proyecto.
    lideres = await users_svc.get_users_by_permission(Permission.LIDER_PROYECTO)
    detalle.revisores = [
        RevisorInfo(revisor_id=int(uid), nombre=(info or {}).get("nombre")) for uid, info in lideres.items()
    ]
    es_encargado = user_id == etapa.encargado_id
    return ProcesoActoDetalle(
        **detalle.model_dump(),
        etapa_tipo=proceso.etapa_tipo,
        etapa_ref_id=proceso.etapa_ref_id,
        tipo_documento=proceso.tipo_documento,
        expediente_id=etapa.expediente_id,
        expediente_radicado=etapa.radicado,
        activo=bool(proceso.activo),
        encargado_id=etapa.encargado_id,
        encargado_nombre=nombres.get(etapa.encargado_id) if etapa.encargado_id else None,
        acto_id=etapa.acto_id,
        puede_cargar_version_final=bool(proceso.activo) and es_encargado and proceso.estado == APROBADO_FIRMA,
        pasos=_pasos(proceso.estado, detalle.revisiones),
    ).model_dump(mode="json")


async def _etapa_del_proceso(db: AsyncSession, proceso_id: int) -> EtapaActo:
    """Bloquea la etapa del proceso (antes que el proceso). 403 si no es de acto."""
    fila = (await db.execute(
        select(DocumentoProceso.etapa_tipo, DocumentoProceso.etapa_ref_id).where(DocumentoProceso.id == proceso_id)
    )).first()
    if fila is None or fila[0] not in ETAPAS_ACTO:
        raise HTTPException(status_code=403, detail="No tienes acceso a este proceso")
    return await cargar_etapa(db, fila[0], fila[1], para_actualizar=True)


def _validar_extension(archivo: UploadFile, extensiones) -> None:
    if not (archivo.filename or "").lower().endswith(tuple(extensiones)):
        raise HTTPException(status_code=400, detail=f"Formato no permitido. Permitidos: {', '.join(extensiones)}")


# ═══════════════════════════════════════════════════════════════ consultas

@router.get("/etapa/{etapa_tipo}/{etapa_ref_id}", status_code=200)
async def estado_etapa(request: Request, etapa_tipo: str, etapa_ref_id: int, db: AsyncSession = Depends(get_db_managed)):
    """Estado del acto de una etapa para pintar su panel: proceso vigente
    (detalle) o null, y qué puede hacer el usuario."""
    user_id = int(verify_gateway_token(request)["user_id"])
    etapa = await cargar_etapa(db, etapa_tipo, etapa_ref_id)
    if not await _puede_ver_etapa(user_id, etapa):
        raise HTTPException(status_code=403, detail="No tienes acceso a este expediente")

    proceso = await proceso_vigente(db, etapa_tipo, etapa_ref_id)
    en_curso = proceso is not None and proceso.estado not in (APROBADO, FINALIZADO)
    es_encargado = user_id == etapa.encargado_id
    es_super = await users_svc.verify_permission(user_id, Permission.MANUAL_UPLOAD)
    encargado_nombre = None
    if etapa.encargado_id:
        usuarios = await users_svc.get_user_info([etapa.encargado_id])
        info = usuarios.get(etapa.encargado_id) or usuarios.get(str(etapa.encargado_id)) or {}
        encargado_nombre = info.get("nombre")
    return JSONResponse(content={
        "ok": True,
        "etapa_tipo": etapa_tipo,
        "etapa_ref_id": etapa_ref_id,
        "expediente_id": etapa.expediente_id,
        "acto_id": etapa.acto_id,
        "encargado_id": etapa.encargado_id,
        "encargado_nombre": encargado_nombre,
        "es_encargado": es_encargado,
        "puede_proyectar": es_encargado and not etapa.acto_id and not en_curso,
        "puede_cargue_directo": es_super and not etapa.acto_id,
        "proceso": await _detalle(db, proceso.id, user_id) if proceso is not None else None,
    })


@router.get("/{proceso_id}", status_code=200)
async def detalle_proceso(request: Request, proceso_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = int(verify_gateway_token(request)["user_id"])
    return JSONResponse(content=await _detalle(db, proceso_id, user_id))


# ═══════════════════════════════════════════════════════════════ iniciar

@router.post("/iniciar", status_code=200)
async def iniciar_proceso(
    request: Request,
    etapa_tipo: str = Form(...),
    etapa_ref_id: int = Form(...),
    db: AsyncSession = Depends(get_db_managed),
):
    """El encargado abre el proceso del acto en ``pendiente_carga`` (versión 0)
    y sube la primera versión desde el modal del proceso (``/{id}/versiones``),
    como en recurso. Idempotente: si ya hay uno en curso devuelve ese (200);
    si lo crea, 201."""
    user_id = int(verify_gateway_token(request)["user_id"])
    try:
        etapa = await cargar_etapa(db, etapa_tipo, etapa_ref_id, para_actualizar=True)
        proceso, creado = await iniciar(db, etapa, user_id=user_id)
        await db.commit()
    except ReviewError as e:
        await db.rollback()
        raise _http(e)
    except HTTPException:
        await db.rollback()
        raise

    return JSONResponse(status_code=201 if creado else 200, content={
        "ok": True,
        "proceso_id": proceso.id,
        "creado": creado,
        "estado": FLUJO.estado_info(proceso.estado).model_dump(),
    })


# ═══════════════════════════════════════════════════════════════ proyectar

@router.post("/proyectar", status_code=201)
async def proyectar_acto(
    request: Request,
    etapa_tipo: str = Form(...),
    etapa_ref_id: int = Form(...),
    archivo: UploadFile = File(...),
    comentario: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db_managed),
):
    """El encargado del expediente sube el proyecto del acto (v1, pdf/doc/docx):
    el proceso queda ``en_revision`` y se avisa a los líderes de proyecto."""
    user_id = int(verify_gateway_token(request)["user_id"])
    try:
        etapa = await cargar_etapa(db, etapa_tipo, etapa_ref_id, para_actualizar=True)
        if etapa.encargado_id != user_id:
            raise PermisoDenegado("Solo el encargado del expediente puede proyectar el acto")
        if etapa.acto_id:
            raise HTTPException(status_code=409, detail="La etapa ya tiene su acto administrativo")
        _validar_extension(archivo, FLUJO.extensiones_version)
        ref = await _subir_a_docs(archivo)
        proceso = await proyectar(db, etapa, user_id=user_id, archivo=ref, comentario=comentario)
        avisos = Avisos(proceso.id)
        await avisos_tras_version(avisos, proceso, 1, proceso.estado, etapa.radicado, user_id)
        await db.commit()
    except ReviewError as e:
        await db.rollback()
        raise _http(e)
    except HTTPException:
        await db.rollback()
        raise

    await avisos.enviar()
    return JSONResponse(status_code=201, content={
        "ok": True,
        "proceso_id": proceso.id,
        "estado": FLUJO.estado_info(proceso.estado).model_dump(),
        "message": "Acto enviado a revisión del líder de proyecto",
    })


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
    """Líder de proyecto: ``aprobado_firma`` | ``devuelto`` (comentario
    obligatorio; adjunto opcional pdf/doc/docx con las observaciones)."""
    user_id = int(verify_gateway_token(request)["user_id"])
    svc = servicio()
    tiene_adjunto = adjunto is not None and bool(adjunto.filename)

    try:
        etapa = await _etapa_del_proceso(db, proceso_id)
        ctx = await svc.contexto(db, proceso_id, para_actualizar=True)
        if not await FLUJO.puede_revisar(ctx, user_id):
            raise PermisoDenegado("Solo el líder de proyecto puede revisar actos administrativos")
        if not ctx.proceso.activo:
            raise HTTPException(status_code=409, detail="Este proceso de revisión ya no está vigente. Recarga")
        acc = FLUJO.acciones.get(accion)
        if acc is None or not FLUJO.accion_aplicable(ctx.proceso, acc):
            raise HTTPException(status_code=400, detail=f"Acción de revisión inválida: {accion}")
        ref = None
        if tiene_adjunto:
            # Validar antes de subir para no dejar archivos huérfanos en app-docs.
            if not acc.admite_adjunto:
                raise HTTPException(status_code=400, detail="Solo se puede adjuntar un archivo al devolver")
            _validar_extension(adjunto, acc.adjunto_extensiones)
            ref = await _subir_a_docs(adjunto)

        res = await svc.revisar(db, proceso_id, user_id=user_id, accion=accion, comentario=comentario, adjunto=ref)
        proceso: DocumentoProceso = res.proceso
        avisos = Avisos(proceso.id)
        await avisos_tras_revision(avisos, proceso, res.estado_nuevo, etapa.radicado, ref is not None, etapa.encargado_id)
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
        "estado": FLUJO.estado_info(res.estado_nuevo).model_dump(),
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
    """Primera versión (``pendiente_carga``, tras ``/iniciar``) o corrección del
    encargado tras una devolución (``rechazado``): debe ser un archivo que no
    esté ya en el proceso (409) y queda ``en_revision``. En ``aprobado_firma``
    la firmada va por ``/version-final`` (409 aquí)."""
    user_id = int(verify_gateway_token(request)["user_id"])
    svc = servicio()
    try:
        etapa = await _etapa_del_proceso(db, proceso_id)
        ctx = await svc.contexto(db, proceso_id, para_actualizar=True)
        if not await FLUJO.puede_subir_version(ctx, user_id):
            raise PermisoDenegado("Solo el encargado del expediente puede subir versiones del acto")
        if not ctx.proceso.activo:
            raise HTTPException(status_code=409, detail="Este proceso de revisión ya no está vigente. Recarga")
        if ctx.proceso.estado == APROBADO_FIRMA:
            raise HTTPException(status_code=409, detail=MOTIVO_VERSION_FINAL)
        if not FLUJO.subida_permitida_en(ctx.proceso):
            raise HTTPException(status_code=400, detail="Solo puedes subir una versión con el acto pendiente de carga o devuelto")
        _validar_extension(archivo, FLUJO.extensiones_subida(ctx.proceso))
        ref = await _subir_a_docs(archivo)

        res = await svc.subir_version(db, proceso_id, user_id=user_id, archivo=ref, comentario=comentario)
        proceso: DocumentoProceso = res.proceso
        avisos = Avisos(proceso.id)
        await avisos_tras_version(avisos, proceso, res.version.numero_version, res.estado_nuevo, etapa.radicado, user_id)
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
        "version": res.version.numero_version,
        "version_id": res.version.id,
        "estado": FLUJO.estado_info(res.estado_nuevo).model_dump(),
        "message": "Versión subida exitosamente",
    })


# ══════════════════════════════════════════════════════ versión final

@router.post("/{proceso_id}/version-final", status_code=200)
async def cargar_version_final_acto(
    request: Request,
    proceso_id: int,
    archivo: UploadFile = File(...),
    tipo_acto: str = Form(...),
    numerado: str = Form(...),
    fecha_numerado: str = Form(...),
    comentario: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db_managed),
):
    """El encargado carga la versión firmada (PDF) del acto ``aprobado_firma``
    con tipo (AUTO|RES), numerado (≤4 dígitos) y fecha. Se auto-aprueba y se
    crea el acto enlazado a la etapa, todo en una transacción."""
    user_id = int(verify_gateway_token(request)["user_id"])
    svc = servicio()
    try:
        etapa = await _etapa_del_proceso(db, proceso_id)
        ctx = await svc.contexto(db, proceso_id, para_actualizar=True)
        if not await FLUJO.puede_subir_version(ctx, user_id):
            raise PermisoDenegado("Solo el encargado del expediente puede cargar la versión final del acto")
        if not ctx.proceso.activo or ctx.proceso.estado != APROBADO_FIRMA:
            raise HTTPException(status_code=409, detail="El acto aún no está aprobado para firma. Recarga")
        if etapa.acto_id:
            raise HTTPException(status_code=409, detail="La etapa ya tiene su acto administrativo")
        # Todo lo validable va antes de subir el archivo (no dejar huérfanos en app-docs).
        tipo, numero, fecha = validar_datos_acto(tipo_acto, numerado, fecha_numerado)
        await validar_numerado_disponible(db, numero, fecha)
        if not (archivo.filename or "").lower().endswith(EXTENSION_PDF):
            raise HTTPException(status_code=400, detail="La versión final firmada debe ser un PDF")
        ref = await _subir_a_docs(archivo)

        res = await cargar_version_final(
            db, proceso_id, user_id=user_id, archivo=ref, comentario=comentario or "Versión final firmada",
        )
        proceso: DocumentoProceso = res.proceso
        acto = await crear_acto(db, etapa, tipo_acto=tipo, numero=numero, fecha=fecha, file_id=ref.file_id)
        # El proceso ya contó un uso de la versión; el acto cuenta el suyo (borrar el acto no la deja huérfana).
        await svc._incrementar_usos([ref.file_id])
        audit = await insert_log(
            db=db,
            tipo_evento="CREAR_ACTO_ADMIN",
            resultado="EXITOSO",
            usuario_id=user_id,
            detalle=f"Creación de acto administrativo {tipo} {numero} (versión final del proceso de revisión)",
            expediente_id=etapa.expediente_id,
            expediente_radicado=etapa.radicado,
            datos_nuevos={
                "tipo_acto": tipo, "numerado": numero, "fecha_numerado": fecha.isoformat(),
                "etapa_tipo": etapa.etapa_tipo, "proceso_id": proceso.id,
            },
        )
        if not audit.get("ok"):
            raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")
        avisos = Avisos(proceso.id)
        await avisos_tras_version(avisos, proceso, res.version.numero_version, res.estado_nuevo, etapa.radicado, user_id)
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
        "version": res.version.numero_version,
        "version_id": res.version.id,
        "estado": FLUJO.estado_info(res.estado_nuevo).model_dump(),
        "acto": {
            "id": acto.id,
            "tipo_acto": acto.tipo_acto,
            "numerado": acto.numerado,
            "fecha_numerado": acto.fecha_numerado.isoformat(),
            "documento_acto_id": acto.documento_acto_administrativo_id,
        },
        "message": "Versión firmada cargada: acto administrativo creado",
    })


# ═══════════════════════════════════════════════════════════════ descargas

@router.get("/{proceso_id}/versiones/{version_id}/descarga")
async def descargar_version(request: Request, proceso_id: int, version_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = int(verify_gateway_token(request)["user_id"])
    await _contexto_visible(db, proceso_id, user_id)
    version = await db.scalar(select(DocumentoProcesoVersion).where(
        DocumentoProcesoVersion.id == version_id, DocumentoProcesoVersion.proceso_id == proceso_id
    ))
    if version is None:
        raise HTTPException(status_code=404, detail="Versión no encontrada")
    return await _stream_archivo(version.file_id, version.archivo_nombre)


@router.get("/{proceso_id}/revisiones/{revision_id}/adjunto")
async def descargar_adjunto(request: Request, proceso_id: int, revision_id: int, db: AsyncSession = Depends(get_db_managed)):
    user_id = int(verify_gateway_token(request)["user_id"])
    await _contexto_visible(db, proceso_id, user_id)
    revision = await db.scalar(select(DocumentoProcesoRevision).where(
        DocumentoProcesoRevision.id == revision_id, DocumentoProcesoRevision.proceso_id == proceso_id
    ))
    if revision is None or not revision.adjunto_url:
        raise HTTPException(status_code=404, detail="Adjunto no encontrado")
    return await _stream_archivo(revision.adjunto_file_id, revision.adjunto_nombre or "adjunto")
