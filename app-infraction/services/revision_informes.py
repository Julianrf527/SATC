"""Flujo de revisión PROPIO del informe técnico (antes en app-docs).

- ``FlujoInformeTecnico``: extiende ``FlujoRevision`` de satc_shared con
  ``aprobado_firma`` (admite borrador Word; la versión firmada, en PDF, se
  auto-aprueba), regla "aprobar exige PDF" y permisos del informe.
- Helpers transaccionales que usan las rutas (``/informes`` y
  ``/revision-informes``): crear/cerrar el proceso vigente y aplicar la
  aprobación al ``InformeTecnico`` en la MISMA transacción que la revisión.
- Notificaciones (las que antes enviaba app-docs + las propias de
  infracciones). Se acumulan durante la operación y se envían DESPUÉS del
  commit (best-effort, nunca abortan la operación).

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
    ErrorUsoArchivo,
    Estado,
    FlujoRevision,
    ProcesoNoEncontrado,
    ProcesoRevisionService,
)

from core.permission import Permission
from db.models.expediente import Expediente
from db.models.informe_proceso import MODELOS_INFORME, InformeProceso
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
    # Tras "aprobado para firma" el profesional sube la versión firmada.
    estados_subida = FlujoRevision.estados_subida | {APROBADO_FIRMA}

    # ---------------------------------------------------------- permisos
    async def puede_ver(self, ctx, user_id: int) -> bool:
        p = ctx.proceso
        if user_id in (p.creador_id, p.asignador_id):
            return True
        if user_id in await ctx.revisores_ids():
            return True
        return await users_svc.verify_permission(user_id, Permission.ASSIGN_REPORTS)

    # Revisar: revisor asignado (default). Subir: profesional = creador (default).

    # ------------------------------------------------------- validaciones
    def extensiones_subida(self, proceso) -> tuple[str, ...]:
        # La versión firmada se auto-aprueba y se une al PDF del expediente.
        if proceso.estado == APROBADO_FIRMA:
            return EXTENSION_PDF
        return super().extensiones_subida(proceso)

    async def validar_accion(self, ctx, accion: Accion, user_id: int) -> str | None:
        motivo = await super().validar_accion(ctx, accion, user_id)
        if motivo or accion.codigo != APROBADO:
            return motivo
        version = await ctx.ultima_version()
        if version is None or not version.archivo_nombre.lower().endswith(".pdf"):
            return (
                "Para aprobar el informe técnico la versión debe estar en PDF. "
                "Devuélvelo pidiendo la versión en PDF o apruébalo para firma."
            )
        return None

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


def servicio() -> ProcesoRevisionService:
    # files_client se resuelve en cada llamada para que los tests puedan sustituirlo.
    return ProcesoRevisionService(MODELOS_INFORME, FLUJO, files=docs_svc.files_client)


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

async def proceso_vigente(
    db: AsyncSession, informe_id: int, *, para_actualizar: bool = False
) -> Optional[InformeProceso]:
    stmt = select(InformeProceso).where(InformeProceso.informe_id == informe_id, InformeProceso.activo.is_(True))
    if para_actualizar:
        stmt = stmt.with_for_update()
    return await db.scalar(stmt)


async def procesos_vigentes(db: AsyncSession, informe_ids: list[int]) -> dict[int, InformeProceso]:
    if not informe_ids:
        return {}
    filas = (await db.execute(
        select(InformeProceso).where(InformeProceso.informe_id.in_(informe_ids), InformeProceso.activo.is_(True))
    )).scalars().all()
    return {p.informe_id: p for p in filas}


def es_final(proceso: Optional[InformeProceso]) -> bool:
    return proceso is not None and proceso.estado in (APROBADO, FINALIZADO)


def resumen_proceso(proceso: Optional[InformeProceso], user_id: int, revisor_id: Optional[int] = None) -> dict:
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
) -> InformeProceso:
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
        campos={"informe_id": informe.id, "asignador_id": asignador_id, "activo": True},
    )
    avisos.agregar(profesional_id, f"{_encabezado(radicado)}Informe técnico de {tipo} asignado")
    avisos.agregar(revisor_id, f"{_encabezado(radicado)}Asignado para revisión: informe técnico de {tipo}")
    return proceso


async def cerrar_proceso_vigente(
    db: AsyncSession, informe_id: int, *, usuario_id: int, descripcion: str
) -> Optional[InformeProceso]:
    """Finaliza (si no es final) y desactiva el proceso vigente."""
    proceso = await proceso_vigente(db, informe_id, para_actualizar=True)
    if proceso is None:
        return None
    if proceso.estado not in (APROBADO, FINALIZADO):
        await servicio().finalizar(db, proceso.id, usuario_id=usuario_id, descripcion=descripcion)
    proceso.activo = False
    await db.flush()
    return proceso


async def aplicar_aprobacion(db: AsyncSession, proceso: InformeProceso, avisos: Avisos, radicado: str) -> InformeTecnico:
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


def avisos_revision(avisos: Avisos, proceso: InformeProceso, accion: str, estado_nuevo: str,
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


def avisos_version(avisos: Avisos, proceso: InformeProceso, numero: int, estado_nuevo: str,
                   radicado: str, revisores: list[int]) -> None:
    enc = _encabezado(radicado)
    if estado_nuevo == EN_REVISION:
        for r in revisores:
            avisos.agregar(r, f"{enc}Nueva versión (v{numero}) del informe técnico")
    elif estado_nuevo == APROBADO:
        for r in revisores:
            avisos.agregar(r, f"{enc}Versión firmada cargada (v{numero}), informe técnico aprobado")
