"""Flujo de revisión PROPIO del informe técnico (antes en app-docs).

- ``FlujoInformeTecnico``: extiende ``FlujoRevision`` de satc_shared con
  ``aprobado_firma`` y permisos del informe. Como en app-recurso, el líder
  técnico NO aprueba directo: solo aprueba para firma (o devuelve), y el
  técnico carga la versión firmada en PDF (con la matriz de recursos si es
  VISITA) con ``cargar_version_final``, que la auto-aprueba y acepta el informe.
- Helpers transaccionales que usan las rutas (``/informes`` y
  ``/revision-informes``): crear/cerrar el proceso vigente y aplicar la
  aprobación al ``InformeTecnico`` en la MISMA transacción que la revisión.
- Notificaciones (las que antes enviaba app-docs + las propias de
  infracciones). Se acumulan durante la operación y se envían DESPUÉS del
  commit (best-effort, nunca abortan la operación).

Los procesos viven en la tabla única ``documento_proceso`` (informes y actos)
con ``etapa_tipo = 'informe_tecnico'`` y ``etapa_ref_id`` = id del informe.
Este flujo solo opera procesos de informe: cualquier otro se trata como
inexistente para él.

Ninguna función hace commit: el llamador hace commit/rollback.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from satc_shared.review_process import (
    APROBADO,
    EN_REVISION,
    FINALIZADO,
    PENDIENTE_CARGA,
    RECHAZADO,
    Accion,
    ArchivoRef,
    ErrorUsoArchivo,
    Estado,
    FlujoRevision,
    PermisoDenegado,
    ProcesoNoEncontrado,
    ProcesoRevisionService,
    ResultadoVersion,
    ReviewError,
    SubidaVersion,
    ValidacionError,
)

from core.permission import Permission
from db.models.expediente import Expediente
from db.models.documento_proceso import (
    ETAPA_INFORME,
    MODELOS_DOCUMENTO,
    DocumentoProceso,
    tipo_documento_informe,
)
from db.models.informe_tecnico import InformeTecnico
import services.docs as docs_svc
import services.notification as notif_svc
import services.users as users_svc

logger = logging.getLogger(__name__)

BOGOTA = ZoneInfo("America/Bogota")
APROBADO_FIRMA = "aprobado_firma"
TIPO_NOTIFICACION = "informe_tecnico"
EXTENSION_PDF = (".pdf",)


# ════════════════════════════════════════════════════════════════════ flujo

class FlujoInformeTecnico(FlujoRevision):
    ESTADOS_EXTRA = (Estado(APROBADO_FIRMA, "Aprobado para firma", "warning"),)
    ACCIONES_EXTRA = (
        Accion(
            APROBADO_FIRMA, "Aprobar para firma",
            etiqueta_realizada="Aprobado para firma", tono="success",
            estado_destino=APROBADO_FIRMA, auditoria="aprobar_firma", icono="firmar",
        ),
    )
    # Tras "aprobado para firma" el técnico carga la versión firmada, pero
    # solo por ``cargar_version_final`` (ver ServicioInforme.subida_version).
    estados_subida = FlujoRevision.estados_subida | {APROBADO_FIRMA}

    # ---------------------------------------------------------- permisos
    # Solo procesos de informe (la tabla también guarda los de actos).
    async def puede_ver(self, ctx, user_id: int) -> bool:
        p = ctx.proceso
        if not p.es_informe:
            return False
        if user_id in (p.creador_id, p.asignador_id):
            return True
        if user_id in await ctx.revisores_ids():
            return True
        return await users_svc.verify_permission(user_id, Permission.ASSIGN_REPORTS)

    # Revisar: líder técnico asignado. Subir: técnico = creador.
    async def puede_revisar(self, ctx, user_id: int) -> bool:
        return ctx.proceso.es_informe and await super().puede_revisar(ctx, user_id)

    async def puede_subir_version(self, ctx, user_id: int) -> bool:
        return ctx.proceso.es_informe and await super().puede_subir_version(ctx, user_id)

    # ------------------------------------------------------- validaciones
    def accion_aplicable(self, proceso, accion: Accion) -> bool:
        # "Aprobar" solo existe como cierre interno (auto-aprobación de la
        # versión firmada); el líder técnico aprueba para firma o devuelve.
        return accion.codigo != APROBADO

    def extensiones_subida(self, proceso) -> tuple[str, ...]:
        # La versión firmada se auto-aprueba y se une al PDF del expediente.
        if proceso.estado == APROBADO_FIRMA:
            return EXTENSION_PDF
        return super().extensiones_subida(proceso)

    # ------------------------------------------------------- transiciones
    async def despues_de_subida(self, ctx, version, user_id: int, estado_anterior: str) -> str:
        if estado_anterior == APROBADO_FIRMA:
            revisor = await ctx.ultimo_revisor(APROBADO_FIRMA)
            await ctx.registrar_revision(
                accion=APROBADO,
                revisor_id=revisor or user_id,
                comentarios="Auto-aprobado: versión firmada subida tras aprobación para firma",
            )
            ctx.auditar("aprobar", user_id, f"Versión firmada auto-aprobada (v{version.numero_version})")
            return APROBADO
        return await super().despues_de_subida(ctx, version, user_id, estado_anterior)


FLUJO = FlujoInformeTecnico()

MOTIVO_VERSION_FINAL = (
    "Aprobado para firma: carga la versión firmada (PDF) con \"Cargar versión final\""
)
MOTIVO_EN_REVISION = "El informe está en revisión; podrás subir una nueva versión si te lo devuelven"


class ServicioInforme(ProcesoRevisionService):
    """En ``aprobado_firma`` la subida normal no aplica: la versión firmada va
    por ``cargar_version_final`` (con la matriz si es VISITA), como en recurso."""

    async def subida_version(self, ctx, user_id: int) -> SubidaVersion | None:
        if not await self.flujo.puede_subir_version(ctx, user_id):
            return None
        p = ctx.proceso
        if not p.activo:
            return SubidaVersion(permitida=False, extensiones=[], motivo="Este proceso ya no está vigente")
        if p.estado == APROBADO_FIRMA:
            return SubidaVersion(permitida=False, extensiones=list(EXTENSION_PDF), motivo=MOTIVO_VERSION_FINAL)
        if p.estado == EN_REVISION:
            return SubidaVersion(
                permitida=False, extensiones=list(self.flujo.extensiones_subida(p)), motivo=MOTIVO_EN_REVISION,
            )
        return await super().subida_version(ctx, user_id)


def servicio() -> ServicioInforme:
    # files_client se resuelve en cada llamada para que los tests puedan sustituirlo.
    return ServicioInforme(MODELOS_DOCUMENTO, FLUJO, files=docs_svc.files_client)


class Conflicto(ReviewError):
    status_code = 409


async def cargar_version_final(
    db: AsyncSession, proceso_id: int, *, user_id: int, archivo: ArchivoRef, comentario: Optional[str]
) -> ResultadoVersion:
    """Versión firmada del informe: valida que el proceso esté vigente y en
    ``aprobado_firma``, que ``user_id`` sea el técnico y que sea PDF; la
    registra y el flujo la auto-aprueba (``aprobado``). No hace commit."""
    svc = servicio()
    ctx = await svc.contexto(db, proceso_id, para_actualizar=True)
    p = ctx.proceso
    if not await FLUJO.puede_subir_version(ctx, user_id):
        raise PermisoDenegado("Solo el técnico asignado puede cargar la versión final")
    if not p.activo:
        raise Conflicto("Este proceso de revisión ya no está vigente. Recarga")
    if p.estado != APROBADO_FIRMA:
        raise Conflicto(
            "El informe aún no está aprobado para firma "
            f"(estado: {FLUJO.estado_info(p.estado).etiqueta}). Recarga"
        )
    if not archivo.tiene_extension(EXTENSION_PDF):
        raise ValidacionError("La versión final firmada debe ser un PDF")
    return await svc._agregar_version(ctx, archivo, user_id, comentario)


# ══════════════════════════════════════════════════════════ notificaciones

@dataclass
class Avisos:
    """Notificaciones pendientes de enviar tras el commit."""

    informe_id: int
    items: list[tuple[int, str]] = field(default_factory=list)

    def agregar(self, usuario_id: Optional[int], mensaje: str) -> None:
        if usuario_id and (int(usuario_id), mensaje) not in self.items:
            self.items.append((int(usuario_id), mensaje))

    async def enviar(self) -> None:
        # id_vinculada = id del informe técnico (el frontend navega a "Mis Informes").
        for usuario_id, mensaje in self.items:
            resultado = await notif_svc.create_notification(
                mensaje=mensaje,
                id_vinculada=str(self.informe_id),
                tipo=TIPO_NOTIFICACION,
                usuario_id=usuario_id,
            )
            if not resultado.get("ok"):
                logger.warning(f"Notificación de informe {self.informe_id} a {usuario_id} falló: {resultado}")


async def contexto_informe(db: AsyncSession, informe_id: int) -> tuple[Optional[InformeTecnico], str]:
    """(informe, radicado) para mensajes."""
    informe = await db.scalar(select(InformeTecnico).where(InformeTecnico.id == informe_id))
    radicado = None
    if informe is not None:
        radicado = await db.scalar(select(Expediente.radicado).where(Expediente.id == informe.expediente_id))
    return informe, radicado or (str(informe.expediente_id) if informe else "?")


def _encabezado(radicado: str) -> str:
    return f"Expediente {radicado}\n"


# ══════════════════════════════════════════════════════ proceso vigente

def _de_informe(*condiciones):
    return (DocumentoProceso.etapa_tipo == ETAPA_INFORME, *condiciones)


async def proceso_vigente(
    db: AsyncSession, informe_id: int, *, para_actualizar: bool = False
) -> Optional[DocumentoProceso]:
    stmt = select(DocumentoProceso).where(
        *_de_informe(DocumentoProceso.etapa_ref_id == informe_id, DocumentoProceso.activo.is_(True))
    )
    if para_actualizar:
        stmt = stmt.with_for_update()
    return await db.scalar(stmt)


async def procesos_vigentes(db: AsyncSession, informe_ids: list[int]) -> dict[int, DocumentoProceso]:
    if not informe_ids:
        return {}
    filas = (await db.execute(
        select(DocumentoProceso).where(
            *_de_informe(DocumentoProceso.etapa_ref_id.in_(informe_ids), DocumentoProceso.activo.is_(True))
        )
    )).scalars().all()
    return {p.etapa_ref_id: p for p in filas}


def es_final(proceso: Optional[DocumentoProceso]) -> bool:
    return proceso is not None and proceso.estado in (APROBADO, FINALIZADO)


def resumen_proceso(proceso: Optional[DocumentoProceso], user_id: int, revisor_id: Optional[int] = None) -> dict:
    """Campos del proceso vigente para listados (/informes, /informes/mios, etapa)."""
    if proceso is None:
        return {
            "proceso_id": None,
            "estado_proceso": None,
            "proceso_activo": False,
            "numero_devoluciones": 0,
            "version_actual": 0,
            "requiere_mi_accion": False,
        }
    estado = FLUJO.estado_info(proceso.estado).model_dump()
    soy_profesional = proceso.creador_id == user_id
    soy_revisor = revisor_id is not None and revisor_id == user_id
    requiere = (
        (soy_profesional and proceso.estado in (PENDIENTE_CARGA, RECHAZADO, APROBADO_FIRMA))
        or (soy_revisor and proceso.estado == EN_REVISION)
    )
    return {
        "proceso_id": proceso.id,
        "estado_proceso": estado,
        "proceso_activo": not es_final(proceso),
        "numero_devoluciones": proceso.numero_devoluciones or 0,
        "version_actual": proceso.version_actual or 0,
        "requiere_mi_accion": requiere,
    }


async def crear_proceso_informe(
    db: AsyncSession,
    informe: InformeTecnico,
    *,
    profesional_id: int,
    revisor_id: int,
    asignador_id: int,
    radicado: str,
    avisos: Avisos,
    reasignacion: bool = False,
) -> DocumentoProceso:
    """Crea el proceso (sin archivo -> ``pendiente_carga``) y lo deja vigente."""
    tipo = informe.tipo_informe or "VISITA"
    proceso = await servicio().crear_proceso(
        db,
        nombre=f"Informe {informe.tipo_informe or 'Técnico'} - Expediente {radicado}",
        descripcion=(
            f"Informe técnico de {tipo}{' (reasignación)' if reasignacion else ''}. "
            "Profesional responsable del cargue."
        ),
        creador_id=profesional_id,
        revisores_ids=[revisor_id],
        usuario_id=asignador_id,
        campos={
            "expediente_id": informe.expediente_id,
            "tipo_documento": tipo_documento_informe(informe.tipo_informe),
            "etapa_tipo": ETAPA_INFORME,
            "etapa_ref_id": informe.id,
            "asignador_id": asignador_id,
            "activo": True,
        },
    )
    avisos.agregar(profesional_id, f"{_encabezado(radicado)}Informe técnico de {tipo} asignado")
    avisos.agregar(revisor_id, f"{_encabezado(radicado)}Asignado para revisión: informe técnico de {tipo}")
    return proceso


async def cerrar_proceso_vigente(
    db: AsyncSession, informe_id: int, *, usuario_id: int, descripcion: str
) -> Optional[DocumentoProceso]:
    """Finaliza (si no es final) y desactiva el proceso vigente."""
    proceso = await proceso_vigente(db, informe_id, para_actualizar=True)
    if proceso is None:
        return None
    if proceso.estado not in (APROBADO, FINALIZADO):
        await servicio().finalizar(db, proceso.id, usuario_id=usuario_id, descripcion=descripcion)
    proceso.activo = False
    await db.flush()
    return proceso


async def aplicar_aprobacion(db: AsyncSession, proceso: DocumentoProceso, avisos: Avisos, radicado: str) -> InformeTecnico:
    """Rama de éxito del antiguo ``_sincronizar_informe``, en la misma transacción
    que la revisión/subida que aprobó el proceso: fechas, archivo del informe
    (que el PDF unificado del expediente toma de ``documento_informe_id``),
    uso propio del archivo y aviso al abogado responsable."""
    informe = await db.scalar(
        select(InformeTecnico).where(InformeTecnico.id == proceso.informe_id).with_for_update()
    )
    if informe is None:
        raise ProcesoNoEncontrado("Informe técnico no encontrado")
    ctx = await servicio().contexto(db, proceso.id)
    version = await ctx.ultima_version()

    hoy = datetime.now(BOGOTA).date()
    fecha_subida = version.fecha_subida if version is not None else None
    informe.fecha_aceptacion_informe = hoy
    informe.fecha_recibido_informe = _fecha_bogota(fecha_subida) or hoy
    informe.documento_informe_id = version.file_id if version is not None else None
    await db.flush()

    # El informe es un uso propio del archivo, aparte de la versión del proceso;
    # se descuenta al cambiar de modo (ver /informes/{id}/cambiar-modo).
    if informe.documento_informe_id:
        try:
            await docs_svc.files_client.increment_usage([informe.documento_informe_id])
        except Exception as e:
            raise ErrorUsoArchivo(f"No se pudo registrar el uso del archivo del informe: {e}") from e

    expediente = await db.scalar(select(Expediente).where(Expediente.id == informe.expediente_id))
    if expediente is not None and expediente.abogado_responsable_id:
        avisos.agregar(
            expediente.abogado_responsable_id,
            f"{_encabezado(radicado)}Informe técnico aceptado, disponible para revisión",
        )
    return informe


def _fecha_bogota(valor) -> Optional[date]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        if valor.tzinfo is None:
            return valor.date()
        return valor.astimezone(BOGOTA).date()
    return valor


def avisos_revision(avisos: Avisos, proceso: DocumentoProceso, accion: str, estado_nuevo: str,
                    radicado: str, con_adjunto: bool, revisores: list[int]) -> None:
    enc = _encabezado(radicado)
    profesional = proceso.creador_id
    if estado_nuevo == APROBADO:
        avisos.agregar(profesional, f"{enc}Informe técnico aprobado")
    elif estado_nuevo == APROBADO_FIRMA:
        avisos.agregar(profesional, f"{enc}Informe técnico aprobado para firma, sube la versión firmada en PDF")
    elif estado_nuevo == FINALIZADO:
        avisos.agregar(profesional, f"{enc}Informe técnico finalizado tras {proceso.numero_devoluciones} devoluciones")
        aviso = f"{enc}Informe técnico rechazado {proceso.numero_devoluciones} veces, reasignar"
        avisos.agregar(proceso.asignador_id, aviso)
        for r in revisores:
            avisos.agregar(r, aviso)
    elif estado_nuevo == RECHAZADO:
        detalle = ", con documento de observaciones" if con_adjunto else ""
        avisos.agregar(
            profesional,
            f"{enc}Informe técnico devuelto ({proceso.numero_devoluciones}/{FLUJO.max_devoluciones}){detalle}",
        )


def avisos_version(avisos: Avisos, proceso: DocumentoProceso, numero: int, estado_nuevo: str,
                   radicado: str, revisores: list[int]) -> None:
    enc = _encabezado(radicado)
    if estado_nuevo == EN_REVISION:
        for r in revisores:
            avisos.agregar(r, f"{enc}Nueva versión (v{numero}) del informe técnico")
    elif estado_nuevo == APROBADO:
        for r in revisores:
            avisos.agregar(r, f"{enc}Versión firmada cargada (v{numero}), informe técnico aprobado")
