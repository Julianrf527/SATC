"""Servicio genérico del proceso de revisión sobre los modelos concretos de la app.

Convenciones:
- Opera sobre una ``AsyncSession`` de la app y NO hace commit: hace ``flush``
  y deja el commit (o rollback) al llamador, para que la app pueda sumar sus
  propios cambios/notificaciones en la misma transacción.
- No sube archivos: la app sube (``FilesClient.upload`` o su propio pipeline)
  y pasa un ``ArchivoRef``. El servicio valida extensión, guarda la referencia
  e incrementa ``numero_usos`` vía el ``FileUsageTracker``.
- El incremento de ``numero_usos`` se hace tras el flush y antes del commit:
  si falla se lanza ``ErrorUsoArchivo`` (la app debe hacer rollback). Si
  después falla el commit el contador queda inflado, lo que es inocuo (el
  archivo no se borra); lo contrario borraría un archivo referenciado.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional, Protocol, runtime_checkable

from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from .errors import (
    ErrorUsoArchivo,
    PermisoDenegado,
    ProcesoNoEncontrado,
    TransicionInvalida,
    ValidacionError,
    VersionDuplicada,
)
from .flow import FINALIZADO, PENDIENTE_CARGA, Accion, FlujoRevision
from .models import ahora
from .schemas import (
    AccionRevision,
    ArchivoInfo,
    AuditoriaInfo,
    ProcesoDetalle,
    RevisionInfo,
    RevisorInfo,
    SubidaVersion,
    Tono,
    VersionInfo,
)


class ArchivoRef(BaseModel):
    """Referencia a un archivo ya subido a app-docs (``file_hash``)."""

    file_id: Optional[int] = None
    url: str
    nombre: str
    size: Optional[int] = None

    @property
    def extension(self) -> str:
        nombre = self.nombre.lower()
        return nombre[nombre.rfind("."):] if "." in nombre else ""

    def tiene_extension(self, extensiones: Iterable[str]) -> bool:
        return self.nombre.lower().endswith(tuple(e.lower() for e in extensiones))


@runtime_checkable
class FileUsageTracker(Protocol):
    """Lo implementa ``satc_shared.clients.FilesClient``. app-docs, que es
    dueño de ``file_hash``, puede pasar una implementación local sobre su BD."""

    async def increment_usage(self, file_ids: list[int]) -> Any: ...

    async def decrement_usage(self, file_ids: list[int]) -> Any: ...


@dataclass(frozen=True)
class ReviewModels:
    proceso: type
    version: type
    revision: type
    auditoria: type
    asignacion: type


@dataclass
class ResultadoRevision:
    proceso: Any
    revision: Any
    accion: Accion
    estado_anterior: str
    estado_nuevo: str
    descripcion: str

    @property
    def finalizado(self) -> bool:
        return self.estado_nuevo == FINALIZADO


@dataclass
class ResultadoVersion:
    proceso: Any
    version: Any
    estado_anterior: str
    estado_nuevo: str
    inicial: bool


class Contexto:
    """Lo que reciben los hooks del flujo: el proceso cargado y helpers."""

    def __init__(self, service: "ProcesoRevisionService", db: AsyncSession, proceso: Any):
        self.service = service
        self.db = db
        self.proceso = proceso
        self._revisores: list[int] | None = None

    @property
    def models(self) -> ReviewModels:
        return self.service.models

    async def revisores_ids(self) -> list[int]:
        if self._revisores is None:
            A = self.models.asignacion
            rows = await self.db.execute(
                select(A.revisor_id).where(A.proceso_id == self.proceso.id).order_by(A.id)
            )
            self._revisores = [r for (r,) in rows.all()]
        return self._revisores

    async def ultima_version(self) -> Any | None:
        V = self.models.version
        return await self.db.scalar(
            select(V).where(V.proceso_id == self.proceso.id).order_by(V.numero_version.desc()).limit(1)
        )

    async def ultimo_revisor(self, accion: str) -> int | None:
        """Revisor de la revisión más reciente con ese código de acción."""
        R = self.models.revision
        return await self.db.scalar(
            select(R.revisor_id)
            .where(R.proceso_id == self.proceso.id, R.accion == accion)
            .order_by(R.fecha_revision.desc(), R.id.desc())
            .limit(1)
        )

    async def registrar_revision(
        self,
        *,
        accion: str,
        revisor_id: int,
        comentarios: str | None = None,
        adjunto: ArchivoRef | None = None,
    ) -> Any:
        return await self.service._registrar_revision(self, accion, revisor_id, comentarios, adjunto)

    def auditar(
        self, accion: str, usuario_id: int | None, descripcion: str, datos: Mapping[str, Any] | None = None
    ) -> Any:
        return self.service._auditar(self.db, self.proceso, accion, usuario_id, descripcion, datos)


class ProcesoRevisionService:
    def __init__(
        self,
        models: ReviewModels,
        flujo: FlujoRevision,
        files: FileUsageTracker | None = None,
    ):
        self.models = models
        self.flujo = flujo
        self.files = files

    # ================================================================ util
    async def cargar(self, db: AsyncSession, proceso_id: int, *, para_actualizar: bool = False) -> Any:
        P = self.models.proceso
        stmt = select(P).where(P.id == proceso_id)
        if para_actualizar:
            # populate_existing: si el proceso ya estaba en el identity map (p. ej.
            # la app lo leyó para pre-validar antes de subir un archivo), sin esto
            # SQLAlchemy devuelve la instancia cacheada y el lock no refresca el
            # estado leído -> dos revisiones concurrentes verían 'en_revision'.
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        proceso = await db.scalar(stmt)
        if proceso is None:
            raise ProcesoNoEncontrado("Proceso no encontrado")
        return proceso

    async def contexto(self, db: AsyncSession, proceso_id: int, *, para_actualizar: bool = False) -> Contexto:
        return Contexto(self, db, await self.cargar(db, proceso_id, para_actualizar=para_actualizar))

    def _auditar(self, db, proceso, accion, usuario_id, descripcion, datos=None):
        fila = self.models.auditoria(
            proceso_id=proceso.id,
            accion=accion,
            usuario_id=usuario_id,
            descripcion=descripcion,
            datos_adicionales=dict(datos) if datos is not None else None,
        )
        db.add(fila)
        return fila

    async def _incrementar_usos(self, file_ids: list[int]) -> None:
        file_ids = [f for f in file_ids if f]
        if not file_ids or self.files is None:
            return
        try:
            resultado = await self.files.increment_usage(file_ids)
        except Exception as e:  # cualquier fallo de red/servicio
            raise ErrorUsoArchivo(f"No se pudo registrar el uso del archivo: {e}") from e
        ok = getattr(resultado, "ok", None)
        if ok is None and isinstance(resultado, Mapping):
            ok = resultado.get("ok")
        if ok is False:
            raise ErrorUsoArchivo("app-docs rechazó registrar el uso del archivo")

    async def _registrar_revision(self, ctx: Contexto, accion, revisor_id, comentarios, adjunto):
        revision = self.models.revision(
            proceso_id=ctx.proceso.id,
            version_revisada=ctx.proceso.version_actual,
            revisor_id=revisor_id,
            accion=accion,
            comentarios=comentarios,
            adjunto_file_id=adjunto.file_id if adjunto else None,
            adjunto_url=adjunto.url if adjunto else None,
            adjunto_nombre=adjunto.nombre if adjunto else None,
            adjunto_size=adjunto.size if adjunto else None,
            fecha_revision=ahora(),
        )
        ctx.db.add(revision)
        return revision

    # ======================================================== crear_proceso
    async def crear_proceso(
        self,
        db: AsyncSession,
        *,
        nombre: str,
        creador_id: int,
        revisores_ids: Iterable[int],
        descripcion: str | None = None,
        archivo: ArchivoRef | None = None,
        comentario: str | None = None,
        usuario_id: int | None = None,
        campos: Mapping[str, Any] | None = None,
    ) -> Any:
        """Crea el proceso, asigna revisores y, si llega ``archivo``, sube la
        versión 1 (queda ``en_revision``); si no, queda ``pendiente_carga``.
        ``campos``: columnas extra del modelo concreto de la app.
        ``usuario_id``: quien ejecuta (default el creador; p. ej. un servicio
        que crea a nombre de otro)."""
        revisores = list(dict.fromkeys(int(r) for r in revisores_ids))
        if not revisores:
            raise ValidacionError("Debe asignar al menos un revisor")

        proceso = self.models.proceso(
            nombre=nombre,
            descripcion=descripcion,
            creador_id=creador_id,
            estado=PENDIENTE_CARGA,
            version_actual=0,
            numero_devoluciones=0,
            **dict(campos or {}),
        )
        db.add(proceso)
        await db.flush()

        for revisor_id in revisores:
            db.add(self.models.asignacion(proceso_id=proceso.id, revisor_id=revisor_id, notificado=False))
        actor = usuario_id if usuario_id is not None else creador_id
        self._auditar(db, proceso, "crear", actor, f"Proceso creado: {nombre}", {"revisores": revisores})

        if archivo is not None:
            ctx = Contexto(self, db, proceso)
            await self._agregar_version(ctx, archivo, creador_id, comentario)
        await db.flush()
        return proceso

    # ============================================================== revisar
    async def revisar(
        self,
        db: AsyncSession,
        proceso_id: int,
        *,
        user_id: int,
        accion: str,
        comentario: str | None = None,
        adjunto: ArchivoRef | None = None,
    ) -> ResultadoRevision:
        ctx = await self.contexto(db, proceso_id, para_actualizar=True)
        proceso = ctx.proceso

        if not await self.flujo.puede_revisar(ctx, user_id):
            raise PermisoDenegado("No estás asignado como revisor de este proceso")

        acc = self.flujo.acciones.get(accion)
        if acc is None or not self.flujo.accion_aplicable(proceso, acc):
            raise ValidacionError(f"Acción de revisión inválida: {accion}")
        if proceso.estado not in acc.desde:
            raise TransicionInvalida(
                f"No se puede '{acc.etiqueta}' en estado '{self.flujo.estado_info(proceso.estado).etiqueta}'"
            )
        if acc.requiere_comentario and not (comentario or "").strip():
            raise ValidacionError("Esta acción requiere un comentario")
        if adjunto is not None:
            if not acc.admite_adjunto:
                raise ValidacionError("Esta acción no admite archivo adjunto")
            if not adjunto.tiene_extension(acc.adjunto_extensiones):
                raise ValidacionError(
                    f"Formato no permitido. Permitidos: {', '.join(acc.adjunto_extensiones)}"
                )
        motivo = await self.flujo.validar_accion(ctx, acc, user_id)
        if motivo:
            raise ValidacionError(motivo)

        estado_anterior = proceso.estado
        revision = await self._registrar_revision(ctx, acc.codigo, user_id, comentario, adjunto)
        if acc.cuenta_devolucion:
            proceso.numero_devoluciones = (proceso.numero_devoluciones or 0) + 1
        estado_nuevo = self.flujo.estado_tras_accion(proceso, acc)
        proceso.estado = estado_nuevo
        proceso.fecha_ultima_actualizacion = ahora()

        codigo_aud, descripcion = self.flujo.auditoria_accion(proceso, acc, estado_nuevo)
        self._auditar(db, proceso, codigo_aud, user_id, descripcion, {
            "comentarios": comentario,
            "version": proceso.version_actual,
            "adjunto": adjunto.nombre if adjunto else None,
            "estado_anterior": estado_anterior,
        })
        await db.flush()
        if adjunto is not None and adjunto.file_id:
            await self._incrementar_usos([adjunto.file_id])

        return ResultadoRevision(proceso, revision, acc, estado_anterior, estado_nuevo, descripcion)

    # ========================================================= subir_version
    async def subir_version(
        self,
        db: AsyncSession,
        proceso_id: int,
        *,
        user_id: int,
        archivo: ArchivoRef,
        comentario: str | None = None,
    ) -> ResultadoVersion:
        ctx = await self.contexto(db, proceso_id, para_actualizar=True)
        if not await self.flujo.puede_subir_version(ctx, user_id):
            raise PermisoDenegado("No puedes subir versiones en este proceso")
        return await self._agregar_version(ctx, archivo, user_id, comentario)

    async def _agregar_version(
        self, ctx: Contexto, archivo: ArchivoRef, user_id: int, comentario: str | None
    ) -> ResultadoVersion:
        proceso, db = ctx.proceso, ctx.db
        if not self.flujo.subida_permitida_en(proceso):
            raise TransicionInvalida("Solo puedes subir una nueva versión cuando el proceso ha sido devuelto")
        extensiones = self.flujo.extensiones_subida(proceso)
        if not archivo.tiene_extension(extensiones):
            raise ValidacionError(f"Formato no permitido. Permitidos: {', '.join(extensiones)}")
        motivo = await self.flujo.validar_subida(ctx, archivo, user_id)
        if motivo:
            raise ValidacionError(motivo)

        V = self.models.version
        condicion = V.file_id == archivo.file_id if archivo.file_id else V.archivo_url == archivo.url
        existente = await db.scalar(select(V.id).where(V.proceso_id == proceso.id, condicion).limit(1))
        if existente is not None:
            raise VersionDuplicada("Esta versión del archivo ya existe en el proceso")

        estado_anterior = proceso.estado
        inicial = (proceso.version_actual or 0) == 0
        numero = (proceso.version_actual or 0) + 1
        version = V(
            proceso_id=proceso.id,
            numero_version=numero,
            file_id=archivo.file_id,
            archivo_url=archivo.url,
            archivo_nombre=archivo.nombre,
            archivo_size=archivo.size,
            usuario_subida_id=user_id,
            comentario=comentario,
            fecha_subida=ahora(),
        )
        db.add(version)
        proceso.version_actual = numero
        proceso.fecha_ultima_actualizacion = ahora()

        estado_nuevo = await self.flujo.despues_de_subida(ctx, version, user_id, estado_anterior)
        proceso.estado = estado_nuevo
        self._auditar(
            db, proceso,
            "subir_version_inicial" if inicial else "subir_version",
            user_id,
            f"Versión inicial cargada (v{numero})" if inicial else f"Nueva versión subida (v{numero})",
            {"version": numero, "file_id": archivo.file_id, "comentario": comentario,
             "estado_anterior": estado_anterior, "estado_nuevo": estado_nuevo},
        )
        await db.flush()
        if archivo.file_id:
            await self._incrementar_usos([archivo.file_id])
        return ResultadoVersion(proceso, version, estado_anterior, estado_nuevo, inicial)

    # ============================================================ finalizar
    async def finalizar(
        self, db: AsyncSession, proceso_id: int, *, usuario_id: int | None, descripcion: str
    ) -> Any:
        """Cierre forzado (p. ej. la app cancela el proceso). Idempotente."""
        proceso = await self.cargar(db, proceso_id, para_actualizar=True)
        if proceso.estado != FINALIZADO:
            anterior = proceso.estado
            proceso.estado = FINALIZADO
            proceso.fecha_ultima_actualizacion = ahora()
            self._auditar(db, proceso, "finalizar", usuario_id, descripcion, {"estado_anterior": anterior})
            await db.flush()
        return proceso

    # ======================================================= eliminar
    async def eliminar_proceso(self, db: AsyncSession, proceso_id: int) -> None:
        """Borra el proceso y sus hijos y decrementa ``numero_usos`` de todos
        sus archivos (versiones y adjuntos)."""
        proceso = await self.cargar(db, proceso_id, para_actualizar=True)
        M = self.models
        file_ids = [f for (f,) in (await db.execute(
            select(M.version.file_id).where(M.version.proceso_id == proceso.id)
        )).all() if f]
        file_ids += [f for (f,) in (await db.execute(
            select(M.revision.adjunto_file_id).where(M.revision.proceso_id == proceso.id)
        )).all() if f]
        for modelo in (M.auditoria, M.revision, M.version, M.asignacion):
            await db.execute(delete(modelo).where(modelo.proceso_id == proceso.id))
        await db.delete(proceso)
        await db.flush()
        if file_ids and self.files is not None:
            try:
                await self.files.decrement_usage(file_ids)
            except Exception as e:
                raise ErrorUsoArchivo(f"No se pudo liberar el uso de los archivos: {e}") from e

    # ======================================================= detalle / UI
    async def acciones_disponibles(self, ctx: Contexto, user_id: int) -> list[AccionRevision]:
        if not await self.flujo.puede_revisar(ctx, user_id):
            return []
        acciones = []
        for acc in self.flujo.acciones.values():
            if ctx.proceso.estado not in acc.desde or not self.flujo.accion_aplicable(ctx.proceso, acc):
                continue
            bloqueada = await self.flujo.validar_accion(ctx, acc, user_id)
            acciones.append(self.flujo.accion_regla(acc, bloqueada))
        return acciones

    async def subida_version(self, ctx: Contexto, user_id: int) -> SubidaVersion | None:
        if not await self.flujo.puede_subir_version(ctx, user_id):
            return None
        extensiones = list(self.flujo.extensiones_subida(ctx.proceso))
        if not self.flujo.subida_permitida_en(ctx.proceso):
            return SubidaVersion(
                permitida=False, extensiones=extensiones,
                motivo="Solo se puede subir una nueva versión cuando el proceso ha sido devuelto",
            )
        return SubidaVersion(permitida=True, extensiones=extensiones)

    async def detalle(
        self,
        db: AsyncSession,
        proceso_id: int,
        *,
        user_id: int,
        nombres_usuarios: Mapping[int, str] | None = None,
        verificar_acceso: bool = True,
    ) -> ProcesoDetalle:
        """Detalle completo + acciones del usuario. Lanza ``PermisoDenegado``
        si no puede verlo. ``ProcesoNoEncontrado`` si no existe: la app puede
        mapear ambos a 403 para no revelar qué IDs existen."""
        ctx = await self.contexto(db, proceso_id)
        proceso = ctx.proceso
        if verificar_acceso and not await self.flujo.puede_ver(ctx, user_id):
            raise PermisoDenegado("No tienes acceso a este proceso")

        M = self.models
        nombres = dict(nombres_usuarios or {})
        asignaciones = (await db.execute(
            select(M.asignacion).where(M.asignacion.proceso_id == proceso.id).order_by(M.asignacion.id)
        )).scalars().all()
        versiones = (await db.execute(
            select(M.version).where(M.version.proceso_id == proceso.id).order_by(M.version.numero_version.desc())
        )).scalars().all()
        revisiones = (await db.execute(
            select(M.revision).where(M.revision.proceso_id == proceso.id)
            .order_by(M.revision.fecha_revision.desc(), M.revision.id.desc())
        )).scalars().all()
        auditoria = (await db.execute(
            select(M.auditoria).where(M.auditoria.proceso_id == proceso.id)
            .order_by(M.auditoria.fecha_accion, M.auditoria.id)
        )).scalars().all()

        def _accion_meta(codigo: str) -> tuple[str, Tono]:
            acc = self.flujo.acciones.get(codigo)
            if acc is not None:
                return acc.etiqueta_realizada, acc.tono
            evento = self.flujo.evento_auditoria(codigo)
            return evento.etiqueta, evento.tono

        return ProcesoDetalle(
            id=proceso.id,
            nombre=proceso.nombre or "",
            descripcion=proceso.descripcion or "",
            estado=self.flujo.estado_info(proceso.estado),
            version_actual=proceso.version_actual or 0,
            numero_devoluciones=proceso.numero_devoluciones or 0,
            max_devoluciones=self.flujo.max_devoluciones,
            creador_id=proceso.creador_id,
            fecha_creacion=proceso.fecha_creacion,
            fecha_ultima_actualizacion=proceso.fecha_ultima_actualizacion,
            revisores=[
                RevisorInfo(
                    revisor_id=a.revisor_id,
                    nombre=nombres.get(a.revisor_id),
                    fecha_asignacion=a.fecha_asignacion,
                    notificado=bool(a.notificado),
                )
                for a in asignaciones
            ],
            versiones=[
                VersionInfo(
                    version_id=v.id,
                    numero_version=v.numero_version,
                    archivo=ArchivoInfo(file_id=v.file_id, url=v.archivo_url, nombre=v.archivo_nombre, size=v.archivo_size),
                    usuario_subida_id=v.usuario_subida_id,
                    comentario=v.comentario or "",
                    fecha_subida=v.fecha_subida,
                )
                for v in versiones
            ],
            revisiones=[
                RevisionInfo(
                    revision_id=r.id,
                    revisor_id=r.revisor_id,
                    revisor_nombre=nombres.get(r.revisor_id) or f"Usuario {r.revisor_id}",
                    accion=r.accion,
                    accion_etiqueta=_accion_meta(r.accion)[0],
                    tono=_accion_meta(r.accion)[1],
                    comentarios=r.comentarios or "",
                    version_revisada=r.version_revisada,
                    fecha_revision=r.fecha_revision,
                    adjunto=(
                        ArchivoInfo(file_id=r.adjunto_file_id, url=r.adjunto_url, nombre=r.adjunto_nombre, size=r.adjunto_size)
                        if r.adjunto_url else None
                    ),
                )
                for r in revisiones
            ],
            auditoria=[
                AuditoriaInfo(
                    auditoria_id=a.id,
                    usuario_id=a.usuario_id,
                    accion=a.accion,
                    accion_etiqueta=self.flujo.evento_auditoria(a.accion).etiqueta,
                    tono=self.flujo.evento_auditoria(a.accion).tono,
                    descripcion=a.descripcion or "",
                    datos_adicionales=a.datos_adicionales,
                    fecha_accion=a.fecha_accion,
                )
                for a in auditoria
            ],
            acciones_disponibles=await self.acciones_disponibles(ctx, user_id),
            subida_version=await self.subida_version(ctx, user_id),
        )
