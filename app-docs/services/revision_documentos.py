"""Flujo FIJO de revisión del módulo Documentos sobre satc_shared.review_process.

Reglas (las del flujo base, sin extensiones):
  - Acciones desde ``en_revision``: ``aprobado`` -> aprobado; ``devuelto`` ->
    rechazado, o finalizado al llegar a 3 devoluciones.
  - Solo ``devuelto`` admite adjunto (pdf/doc/docx).
  - Nueva versión solo en ``rechazado`` (o ``pendiente_carga``).
Lo único propio de app-docs: los permisos del módulo deben seguir vigentes
(``documento_revisar`` para revisar, ``documento_crear`` para subir versión).

app-docs es dueño de ``file_hash``: ``numero_usos`` se lleva con un tracker
local sobre la misma sesión (no con FilesClient contra sí mismo), así el
incremento se confirma o se deshace con el mismo commit que la versión/revisión.
"""
from collections import Counter

from fastapi import HTTPException
from sqlalchemy import func, update
from sqlalchemy.ext.asyncio import AsyncSession

from satc_shared.review_process import (
    FlujoRevision,
    PermisoDenegado,
    ProcesoNoEncontrado,
    ProcesoRevisionService,
    ReviewError,
    ReviewModels,
    TransicionInvalida,
    ValidacionError,
)

from core.permission import permission
from db.models.asignaciones_revisores import AsignacionRevisor
from db.models.auditoria_documentos import AuditoriaDocumento
from db.models.documentos import Documento
from db.models.file_hash import FileHash
from db.models.revisiones import Revision
from db.models.versiones_documento import VersionDocumento
from services.users import verify_permission

PERMISO_CREADOR = permission.PERMISO_CREADOR
PERMISO_REVISOR = permission.PERMISO_REVISOR

MODELS = ReviewModels(
    proceso=Documento,
    version=VersionDocumento,
    revision=Revision,
    auditoria=AuditoriaDocumento,
    asignacion=AsignacionRevisor,
)


class FlujoDocumentos(FlujoRevision):
    async def puede_revisar(self, ctx, user_id: int) -> bool:
        return await super().puede_revisar(ctx, user_id) and bool(await verify_permission(user_id, PERMISO_REVISOR))

    async def puede_subir_version(self, ctx, user_id: int) -> bool:
        return await super().puede_subir_version(ctx, user_id) and bool(await verify_permission(user_id, PERMISO_CREADOR))


FLUJO = FlujoDocumentos()


class UsoArchivosLocal:
    """``FileUsageTracker`` sobre ``file_hash`` en la sesión de la petición."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _ajustar(self, file_ids: list[int], signo: int) -> None:
        for file_id, veces in Counter(f for f in file_ids if f).items():
            nuevo = FileHash.numero_usos + signo * veces
            if signo < 0:
                nuevo = func.greatest(nuevo, 0)
            await self.db.execute(update(FileHash).where(FileHash.id == file_id).values(numero_usos=nuevo))

    async def increment_usage(self, file_ids: list[int]) -> dict:
        await self._ajustar(file_ids, +1)
        return {"ok": True}

    async def decrement_usage(self, file_ids: list[int]) -> dict:
        await self._ajustar(file_ids, -1)
        return {"ok": True}


def servicio(db: AsyncSession) -> ProcesoRevisionService:
    return ProcesoRevisionService(MODELS, FLUJO, files=UsoArchivosLocal(db))


def http_error(e: ReviewError) -> HTTPException:
    # No existe y no tiene acceso responden igual: no revelar qué IDs existen.
    if isinstance(e, ProcesoNoEncontrado):
        return HTTPException(status_code=403, detail="No tienes acceso a este documento")
    if isinstance(e, PermisoDenegado):
        return HTTPException(status_code=403, detail=e.detail)
    return HTTPException(status_code=e.status_code, detail=e.detail)


# ---------------------------------------------------------------------------
# Pre-validaciones: se corren ANTES de pasar el archivo por el pipeline de
# seguridad y subirlo a MinIO, para no aceptar archivos de quien no puede
# ejecutar la acción. El servicio vuelve a validar todo (con lock) después.
# ---------------------------------------------------------------------------

async def prevalidar_revision(
    svc: ProcesoRevisionService, db: AsyncSession, documento_id: int, user_id: int,
    accion: str, adjunto_nombre: str | None,
) -> None:
    ctx = await svc.contexto(db, documento_id)
    if not await svc.flujo.puede_revisar(ctx, user_id):
        raise PermisoDenegado("No estás asignado como revisor de este documento")
    acc = svc.flujo.acciones.get(accion)
    if acc is None:
        raise ValidacionError("Estado de revisión inválido")
    if ctx.proceso.estado not in acc.desde:
        raise TransicionInvalida("El documento no está en revisión")
    if adjunto_nombre is not None:
        if not acc.admite_adjunto:
            raise ValidacionError("Solo se puede adjuntar un archivo al devolver el documento")
        if not adjunto_nombre.lower().endswith(acc.adjunto_extensiones):
            raise ValidacionError(f"Formato no permitido. Permitidos: {', '.join(acc.adjunto_extensiones)}")


async def prevalidar_subida(
    svc: ProcesoRevisionService, db: AsyncSession, documento_id: int, user_id: int, nombre: str,
) -> None:
    ctx = await svc.contexto(db, documento_id)
    if not await svc.flujo.puede_subir_version(ctx, user_id):
        raise PermisoDenegado("No eres el creador de este documento")
    if not svc.flujo.subida_permitida_en(ctx.proceso):
        raise TransicionInvalida("Solo puedes subir una nueva versión cuando el documento ha sido devuelto")
    extensiones = svc.flujo.extensiones_subida(ctx.proceso)
    if not nombre.lower().endswith(extensiones):
        raise ValidacionError(f"Formato no permitido. Permitidos: {', '.join(extensiones)}")
