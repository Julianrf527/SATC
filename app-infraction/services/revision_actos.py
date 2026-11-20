"""Proceso de revisión de los actos administrativos de infracciones (medida
preventiva, acoger concepto y cierre), sobre la tabla única ``documento_proceso``.

Reglas de negocio (decididas con la usuaria, 2026-11-19), tomadas de app-recurso
salvo donde se indica:

- **Sube versiones** solo el encargado ACTUAL del expediente
  (``expediente.abogado_responsable_id``), comprobado en cada acción (a
  diferencia de recurso, donde es el ``creador_id`` del proceso): si se
  reasigna el expediente, el nuevo encargado continúa el proceso.
- **Revisa** cualquier usuario con ``infraccion_lider_proyecto`` (por permiso,
  sin asignación). Solo puede **aprobar para firma** o **devolver** (comentario
  obligatorio, documento de observaciones opcional pdf/doc/docx).
- Devolver → ``rechazado``; la corrección (un archivo que no esté ya en el
  proceso) vuelve a ``en_revision`` y el líder revisa OTRA vez: nunca se
  aprueba sola (a diferencia de recurso, donde quien devolvió "ya revisó").
- Sin tope de devoluciones.
- En ``aprobado_firma`` el encargado carga la versión firmada (PDF) con los
  datos del acto (tipo, numerado, fecha) desde la etapa: se auto-aprueba y se
  crea el acto (``crear_acto_desde_version_final``).
- Super gestión carga el acto directo (sin revisión) y cierra el proceso
  vigente (``cerrar_proceso_vigente``).

Ninguna función hace commit.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from satc_shared.review_process import (
    APROBADO,
    EN_REVISION,
    FINALIZADO,
    RECHAZADO,
    Accion,
    ArchivoRef,
    Estado,
    FlujoRevision,
    PermisoDenegado,
    ProcesoRevisionService,
    ResultadoVersion,
    ReviewError,
    SubidaVersion,
    ValidacionError,
)
from satc_shared.review_process.models import ahora

from core.permission import Permission
from db.models.acto_administrativo import ActoAdministrativo
from db.models.documento_proceso import (
    ETAPA_CIERRE,
    ETAPA_CONCEPTO,
    ETAPA_MEDIDA,
    ETAPAS_ACTO,
    MODELOS_DOCUMENTO,
    TIPO_ACTO_POR_ETAPA,
    DocumentoProceso,
)
from db.models.etapa_acoger_concepto import EtapaAcogerConcepto
from db.models.etapa_cierre import EtapaCierre
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.expediente import Expediente
from db.models.medida_preventiva import MedidaPreventiva
import services.docs as docs_svc
import services.notification as notif_svc
import services.users as users_svc

logger = logging.getLogger(__name__)

APROBADO_FIRMA = "aprobado_firma"
# app-users guarda ``notificacion.tipo`` en String(15).
TIPO_NOTIFICACION = "acto_infraccion"
EXTENSION_PDF = (".pdf",)
TIPOS_ACTO = ("AUTO", "RES")
# Sin tope de devoluciones: un valor muy alto equivale a "sin límite" sin tocar el paquete compartido.
SIN_TOPE = 9999

ETIQUETAS_ETAPA = {
    ETAPA_MEDIDA: "Acto de la medida preventiva",
    ETAPA_CONCEPTO: "Acto de acoger concepto",
    ETAPA_CIERRE: "Acto de cierre",
}

MOTIVO_VERSION_FINAL = (
    "Aprobado para firma: carga la versión firmada (PDF) con los datos del acto desde la etapa"
)
MOTIVO_EN_REVISION = "El acto está en revisión; podrás subir una nueva versión si te lo devuelven"
MOTIVO_NO_ENCARGADO = "Solo el encargado del expediente puede subir versiones del acto"


class Conflicto(ReviewError):
    status_code = 409


# ═══════════════════════════════════════════════════════════════ etapa

@dataclass
class EtapaActo:
    """Fila de etapa dueña del acto + su expediente."""

    etapa_tipo: str
    fila: object  # MedidaPreventiva | EtapaAcogerConcepto | EtapaCierre
    expediente_id: int
    radicado: Optional[str]
    encargado_id: Optional[int]

    @property
    def ref_id(self) -> int:
        return self.fila.id

    @property
    def acto_id(self) -> Optional[int]:
        return self.fila.acto_administrativo_id

    @property
    def etiqueta(self) -> str:
        return ETIQUETAS_ETAPA[self.etapa_tipo]


async def cargar_etapa(
    db: AsyncSession, etapa_tipo: str, ref_id: int, *, para_actualizar: bool = False
) -> EtapaActo:
    """404 si la etapa no existe; 400 si el tipo no es de acto."""
    if etapa_tipo not in ETAPAS_ACTO:
        raise HTTPException(status_code=400, detail=f"Etapa inválida: {etapa_tipo}")
    Modelo = {ETAPA_MEDIDA: MedidaPreventiva, ETAPA_CONCEPTO: EtapaAcogerConcepto, ETAPA_CIERRE: EtapaCierre}[etapa_tipo]
    if etapa_tipo == ETAPA_MEDIDA:
        stmt = (
            select(MedidaPreventiva, Expediente.id, Expediente.radicado, Expediente.abogado_responsable_id)
            .join(EtapaRespuesta, EtapaRespuesta.id == MedidaPreventiva.etapa_respuesta_id)
            .join(Expediente, Expediente.id == EtapaRespuesta.expediente_id)
            .where(MedidaPreventiva.id == ref_id)
        )
    else:
        stmt = (
            select(Modelo, Expediente.id, Expediente.radicado, Expediente.abogado_responsable_id)
            .join(Expediente, Expediente.id == Modelo.expediente_id)
            .where(Modelo.id == ref_id)
        )
    if para_actualizar:
        stmt = stmt.with_for_update(of=Modelo)
    row = (await db.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Etapa no encontrada")
    fila, expediente_id, radicado, encargado_id = row
    return EtapaActo(etapa_tipo, fila, expediente_id, radicado, encargado_id)


async def encargado_actual(db: AsyncSession, expediente_id: int) -> Optional[int]:
    return await db.scalar(select(Expediente.abogado_responsable_id).where(Expediente.id == expediente_id))


# ════════════════════════════════════════════════════════════════ flujo

class FlujoActo(FlujoRevision):
    ESTADOS_EXTRA = (Estado(APROBADO_FIRMA, "Aprobado para firma", "warning"),)
    ACCIONES_EXTRA = (
        Accion(
            APROBADO_FIRMA, "Aprobar para firma",
            etiqueta_realizada="Aprobado para firma", tono="success",
            estado_destino=APROBADO_FIRMA, auditoria="aprobar_firma", icono="firmar",
        ),
    )
    # APROBADO_FIRMA: solo para ``_agregar_version`` de la versión final.
    estados_subida = FlujoRevision.estados_subida | {APROBADO_FIRMA}
    max_devoluciones = SIN_TOPE

    # ---------------------------------------------------------- permisos
    async def puede_ver(self, ctx, user_id: int) -> bool:
        p = ctx.proceso
        if not p.es_acto:
            return False
        if user_id == p.creador_id or user_id == await encargado_actual(ctx.db, p.expediente_id):
            return True
        for permiso in (Permission.LIDER_PROYECTO, Permission.FILE_CONSULT, Permission.MANUAL_UPLOAD):
            if await users_svc.verify_permission(user_id, permiso):
                return True
        # Quien revisó alguna vez (aunque ya no tenga el permiso) conserva su histórico.
        R = MODELOS_DOCUMENTO.revision
        return await ctx.db.scalar(
            select(R.id).where(R.proceso_id == p.id, R.revisor_id == user_id).limit(1)
        ) is not None

    async def puede_revisar(self, ctx, user_id: int) -> bool:
        return ctx.proceso.es_acto and await users_svc.verify_permission(user_id, Permission.LIDER_PROYECTO)

    async def puede_subir_version(self, ctx, user_id: int) -> bool:
        p = ctx.proceso
        return p.es_acto and user_id == await encargado_actual(ctx.db, p.expediente_id)

    # ------------------------------------------------------- validaciones
    def accion_aplicable(self, proceso, accion: Accion) -> bool:
        # "Aprobar" solo existe como cierre interno (auto-aprobación de la firmada).
        return accion.codigo != APROBADO

    def extensiones_subida(self, proceso) -> tuple[str, ...]:
        if proceso.estado == APROBADO_FIRMA:
            return EXTENSION_PDF
        return super().extensiones_subida(proceso)

    # ------------------------------------------------------- transiciones
    def estado_tras_accion(self, proceso, accion: Accion) -> str:
        if accion.cuenta_devolucion:
            return RECHAZADO  # sin tope: nunca finaliza por devoluciones
        return super().estado_tras_accion(proceso, accion)

    async def despues_de_subida(self, ctx, version, user_id: int, estado_anterior: str) -> str:
        if estado_anterior == APROBADO_FIRMA:
            revisor = await ctx.ultimo_revisor(APROBADO_FIRMA)
            await ctx.registrar_revision(
                accion=APROBADO,
                revisor_id=revisor or user_id,
                comentarios="Auto-aprobado: versión firmada cargada tras la aprobación para firma",
            )
            ctx.auditar("aprobar", user_id, f"Versión firmada auto-aprobada (v{version.numero_version})")
            return APROBADO
        # Corrección tras devolver: el líder de proyecto revisa de nuevo.
        return EN_REVISION


FLUJO = FlujoActo()


class ServicioActo(ProcesoRevisionService):
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


def servicio() -> ServicioActo:
    # files_client se resuelve en cada llamada para que los tests puedan sustituirlo.
    return ServicioActo(MODELOS_DOCUMENTO, FLUJO, files=docs_svc.files_client)


# ════════════════════════════════════════════════════════ proceso vigente

async def proceso_vigente(
    db: AsyncSession, etapa_tipo: str, ref_id: int, *, para_actualizar: bool = False
) -> Optional[DocumentoProceso]:
    stmt = select(DocumentoProceso).where(
        DocumentoProceso.etapa_tipo == etapa_tipo,
        DocumentoProceso.etapa_ref_id == ref_id,
        DocumentoProceso.activo.is_(True),
    )
    if para_actualizar:
        stmt = stmt.with_for_update()
    return await db.scalar(stmt)


async def archivar_vigente(db: AsyncSession, etapa_tipo: str, ref_id: int, *, usuario_id: int, descripcion: str) -> Optional[DocumentoProceso]:
    """Desactiva el proceso vigente (lo finaliza si no es final). Lo usan el
    cargue directo de super gestión y "proyectar" cuando el vigente ya terminó."""
    proceso = await proceso_vigente(db, etapa_tipo, ref_id, para_actualizar=True)
    if proceso is None:
        return None
    if proceso.estado not in (APROBADO, FINALIZADO):
        await servicio().finalizar(db, proceso.id, usuario_id=usuario_id, descripcion=descripcion)
    proceso.activo = False
    await db.flush()
    return proceso


async def _crear_proceso(db: AsyncSession, etapa: EtapaActo, user_id: int) -> DocumentoProceso:
    """Proceso nuevo del acto en ``pendiente_carga`` (versión 0), como el de las
    etapas de recurso. Si había uno terminado (p. ej. super gestión borró el
    acto) queda en el histórico. El llamador ya validó encargado, acto y en curso."""
    vigente = await proceso_vigente(db, etapa.etapa_tipo, etapa.ref_id, para_actualizar=True)
    if vigente is not None:
        vigente.activo = False
        await db.flush()

    nombre = f"{etapa.etiqueta} - Expediente {etapa.radicado or etapa.expediente_id}"
    proceso = DocumentoProceso(
        nombre=nombre[:255],
        descripcion=f"{etapa.etiqueta}. Lo proyecta el encargado del expediente y lo revisa el líder de proyecto.",
        creador_id=user_id,
        estado="pendiente_carga",
        version_actual=0,
        numero_devoluciones=0,
        expediente_id=etapa.expediente_id,
        tipo_documento=TIPO_ACTO_POR_ETAPA[etapa.etapa_tipo],
        etapa_tipo=etapa.etapa_tipo,
        etapa_ref_id=etapa.ref_id,
        activo=True,
    )
    db.add(proceso)
    await db.flush()
    servicio()._auditar(db, proceso, "crear", user_id, f"Proceso creado: {nombre}", {
        "tipo_documento": proceso.tipo_documento, "etapa_tipo": etapa.etapa_tipo, "etapa_ref_id": etapa.ref_id,
    })
    await db.flush()
    return proceso


def _validar_inicio(etapa: EtapaActo, user_id: int) -> None:
    if etapa.encargado_id != user_id:
        raise PermisoDenegado("Solo el encargado del expediente puede proyectar el acto")
    if etapa.acto_id:
        raise Conflicto("La etapa ya tiene su acto administrativo")


async def iniciar(db: AsyncSession, etapa: EtapaActo, *, user_id: int) -> tuple[DocumentoProceso, bool]:
    """Abre el proceso del acto en ``pendiente_carga`` para que el encargado
    suba la primera versión desde el modal del proceso (como recurso).
    Idempotente: si ya hay uno en curso lo devuelve. -> (proceso, creado)."""
    _validar_inicio(etapa, user_id)
    vigente = await proceso_vigente(db, etapa.etapa_tipo, etapa.ref_id, para_actualizar=True)
    if vigente is not None and vigente.estado not in (APROBADO, FINALIZADO):
        return vigente, False
    return await _crear_proceso(db, etapa, user_id), True


async def proyectar(
    db: AsyncSession, etapa: EtapaActo, *, user_id: int, archivo: ArchivoRef, comentario: Optional[str]
) -> DocumentoProceso:
    """Crea el proceso del acto con la v1 (``en_revision``) en un solo paso.
    Solo el encargado actual; la etapa no debe tener acto ni proceso en curso."""
    _validar_inicio(etapa, user_id)
    vigente = await proceso_vigente(db, etapa.etapa_tipo, etapa.ref_id, para_actualizar=True)
    if vigente is not None and vigente.estado not in (APROBADO, FINALIZADO):
        raise Conflicto("El acto ya tiene un proceso de revisión en curso. Recarga")
    proceso = await _crear_proceso(db, etapa, user_id)
    svc = servicio()
    ctx = await svc.contexto(db, proceso.id, para_actualizar=True)
    await svc._agregar_version(ctx, archivo, user_id, comentario)
    await db.flush()
    return proceso


async def cargar_version_final(
    db: AsyncSession, proceso_id: int, *, user_id: int, archivo: ArchivoRef, comentario: Optional[str]
) -> ResultadoVersion:
    """Versión firmada del acto: proceso vigente en ``aprobado_firma``, usuario =
    encargado actual, PDF. Se auto-aprueba (``aprobado``). No hace commit."""
    svc = servicio()
    ctx = await svc.contexto(db, proceso_id, para_actualizar=True)
    p = ctx.proceso
    if not await FLUJO.puede_subir_version(ctx, user_id):
        raise PermisoDenegado("Solo el encargado del expediente puede cargar la versión final del acto")
    if not p.activo:
        raise Conflicto("Este proceso de revisión ya no está vigente. Recarga")
    if p.estado != APROBADO_FIRMA:
        raise Conflicto(
            f"El acto aún no está aprobado para firma (estado: {FLUJO.estado_info(p.estado).etiqueta}). Recarga"
        )
    if not archivo.tiene_extension(EXTENSION_PDF):
        raise ValidacionError("La versión final firmada debe ser un PDF")
    return await svc._agregar_version(ctx, archivo, user_id, comentario)


# ═══════════════════════════════════════════════════════════ datos del acto

def validar_datos_acto(tipo_acto: str, numerado, fecha_numerado: str) -> tuple[str, int, date]:
    """(tipo, numerado, fecha) validados: 400 si no."""
    if tipo_acto not in TIPOS_ACTO:
        raise HTTPException(status_code=400, detail="El tipo de acto debe ser AUTO o RES")
    try:
        numero = int(str(numerado).strip())
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="El numerado debe ser un número")
    if numero <= 0 or len(str(numero)) > 4:
        raise HTTPException(status_code=400, detail="El numerado debe tener como máximo 4 números")
    try:
        fecha = date.fromisoformat(str(fecha_numerado))
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha de numerado inválida (YYYY-MM-DD)")
    return tipo_acto, numero, fecha


async def validar_numerado_disponible(
    db: AsyncSession, numero: int, fecha: date, *, excluir_id: Optional[int] = None
) -> None:
    """Desde 2013 el par (numerado, fecha) es único entre actos."""
    if fecha.year <= 2012:
        return
    stmt = select(ActoAdministrativo.id).where(
        ActoAdministrativo.numerado == numero, ActoAdministrativo.fecha_numerado == fecha,
    )
    if excluir_id is not None:
        stmt = stmt.where(ActoAdministrativo.id != excluir_id)
    if await db.scalar(stmt):
        raise HTTPException(status_code=400, detail=f"El numerado {numero} con fecha {fecha.isoformat()} ya está en uso")


async def crear_acto(
    db: AsyncSession, etapa: EtapaActo, *, tipo_acto: str, numero: int, fecha: date, file_id: int
) -> ActoAdministrativo:
    """Crea el acto y lo enlaza a su etapa (no toca usos de archivos ni hace commit)."""
    acto = ActoAdministrativo(tipo_acto=tipo_acto, numerado=numero, fecha_numerado=fecha,
                              documento_acto_administrativo_id=file_id)
    db.add(acto)
    await db.flush()
    etapa.fila.acto_administrativo_id = acto.id
    await db.flush()
    return acto


# ══════════════════════════════════════════════════════════ notificaciones

@dataclass
class Avisos:
    """Notificaciones pendientes de enviar tras el commit (``id_vinculada`` = id del proceso)."""

    proceso_id: int
    items: list[tuple[int, str]] = field(default_factory=list)

    def agregar(self, usuario_id: Optional[int], mensaje: str) -> None:
        if usuario_id and (int(usuario_id), mensaje) not in self.items:
            self.items.append((int(usuario_id), mensaje))

    async def agregar_lideres(self, mensaje: str, *, excluir: Optional[int] = None) -> None:
        for uid in await users_svc.get_users_by_permission(Permission.LIDER_PROYECTO):
            if uid != excluir:
                self.agregar(uid, mensaje)

    async def enviar(self) -> None:
        for usuario_id, mensaje in self.items:
            try:
                resultado = await notif_svc.create_notification(
                    mensaje=mensaje, id_vinculada=str(self.proceso_id), tipo=TIPO_NOTIFICACION, usuario_id=usuario_id,
                )
            except Exception as e:  # best-effort: nunca aborta la operación ya confirmada
                resultado = {"ok": False, "message": str(e)}
            if not resultado.get("ok"):
                logger.warning(f"Notificación del proceso {self.proceso_id} a {usuario_id} falló: {resultado}")


def encabezado(radicado: Optional[str], etapa_tipo: str) -> str:
    return f"Expediente {radicado or '?'}\n{ETIQUETAS_ETAPA.get(etapa_tipo, 'Acto administrativo')}: "


async def avisos_tras_revision(avisos: Avisos, proceso: DocumentoProceso, estado_nuevo: str,
                               radicado: Optional[str], con_adjunto: bool, encargado: Optional[int]) -> None:
    enc = encabezado(radicado, proceso.etapa_tipo)
    if estado_nuevo == APROBADO_FIRMA:
        avisos.agregar(encargado, f"{enc}aprobado para firma, carga la versión firmada desde la etapa")
    elif estado_nuevo == RECHAZADO:
        detalle = ", con documento de observaciones" if con_adjunto else ""
        avisos.agregar(encargado, f"{enc}devuelto ({proceso.numero_devoluciones}){detalle}")


async def avisos_tras_version(avisos: Avisos, proceso: DocumentoProceso, numero: int, estado_nuevo: str,
                              radicado: Optional[str], user_id: int) -> None:
    enc = encabezado(radicado, proceso.etapa_tipo)
    if estado_nuevo == EN_REVISION:
        await avisos.agregar_lideres(f"{enc}{'para revisión' if numero == 1 else f'nueva versión (v{numero})'}",
                                     excluir=user_id)
    elif estado_nuevo == APROBADO:
        await avisos.agregar_lideres(f"{enc}versión firmada cargada, acto creado", excluir=user_id)


async def procesos_acto_en_curso(db: AsyncSession, expediente_ids: list[int]) -> dict[int, list[DocumentoProceso]]:
    """Procesos de acto vigentes y no terminados por expediente (aviso al reasignar)."""
    if not expediente_ids:
        return {}
    filas = (await db.execute(
        select(DocumentoProceso).where(
            DocumentoProceso.expediente_id.in_(expediente_ids),
            DocumentoProceso.etapa_tipo.in_(ETAPAS_ACTO),
            DocumentoProceso.activo.is_(True),
            DocumentoProceso.estado.notin_((APROBADO, FINALIZADO)),
        )
    )).scalars().all()
    out: dict[int, list[DocumentoProceso]] = {}
    for p in filas:
        out.setdefault(p.expediente_id, []).append(p)
    return out


def marcar_actualizado(proceso: DocumentoProceso) -> None:
    proceso.fecha_ultima_actualizacion = ahora()


async def avisar_reasignacion(db: AsyncSession, radicados: dict[int, Optional[str]], nuevo_encargado: Optional[int]) -> None:
    """Tras reasignar expedientes (ya confirmado): avisa al nuevo encargado de
    cada acto con proceso en curso, que ahora le toca continuar. Best-effort."""
    if not nuevo_encargado:
        return
    try:
        en_curso = await procesos_acto_en_curso(db, list(radicados))
    except Exception as e:
        logger.warning(f"No se pudieron consultar los actos en proceso al reasignar: {e}")
        return
    for expediente_id, procesos in en_curso.items():
        for p in procesos:
            avisos = Avisos(p.id)
            estado = FLUJO.estado_info(p.estado).etiqueta.lower()
            avisos.agregar(nuevo_encargado, f"{encabezado(radicados.get(expediente_id), p.etapa_tipo)}"
                                            f"te corresponde continuar el proceso ({estado})")
            await avisos.enviar()
