"""Motor de revisión de los documentos que se proyectan en app-recurso (plan §5,
DISENO_TECNICO §4).

Extiende ``satc_shared.review_process`` (como ``FlujoInformeTecnico`` de
infraction) con:

- **Cadenas por pasos** (``CADENAS``, ÚNICO lugar donde se configuran): cada
  ``tipo_documento`` tiene una lista de pasos y cada paso es un conjunto de
  permisos de revisor que deben revisar **todos**, en cualquier orden.
  ``documento_proceso.paso_actual`` es el índice del paso y cada fila de
  ``documento_proceso_revision`` guarda ``(paso, permiso)`` con que se revisó.
- Estado extra ``aprobado_firma``: lo alcanza la última aprobación del último
  paso. Luego el encargado carga la versión firmada (solo PDF) desde el endpoint
  de su etapa (``cargar_version_final``) y queda ``aprobado`` automáticamente.
- Devolver registra ``(paso, permiso)`` → ese permiso "ya revisó" ese paso
  (plan §5.2: no revisa dos veces). Al subir la corrección vuelve a
  ``en_revision`` en el MISMO paso y, si ya no queda ningún permiso pendiente en
  él, avanza solo.
- Sin tope de devoluciones (``TODO(negocio)``) ni reasignación.

API pública para las etapas (agente C) — ninguna función hace commit:

    avisos = Avisos()
    proceso = await crear_proceso(db, expediente_id=..., tipo_documento="AUTO_ADMITE",
                                  etapa_tipo="acto_admite", etapa_ref_id=fila.id,
                                  encargado_id=yo, usuario_id=yo, avisos=avisos)
    ...
    proceso = await proceso_vigente(db, "acto_admite", fila.id, para_actualizar=True)
    await cargar_version_final(db, proceso, archivo_ref, user_id, avisos)  # -> aprobado
    acto = await services.actos.crear_acto(...)
    await db.commit(); await avisos.enviar()

Errores: lanzan ``ReviewError`` (``status_code`` + ``detail``); la ruta los
traduce con ``http_error(e)``.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from satc_shared.clients import ServiceClientError
from satc_shared.review_process import (
    APROBADO,
    DEVUELTO,
    EN_REVISION,
    FINALIZADO,
    PENDIENTE_CARGA,
    RECHAZADO,
    Accion,
    AccionRevision,
    ArchivoRef,
    Contexto,
    Estado,
    EventoAuditoria,
    FlujoRevision,
    PermisoDenegado,
    ProcesoRevisionService,
    ResultadoRevision,
    ResultadoVersion,
    ReviewError,
    SubidaVersion,
    TransicionInvalida,
    ValidacionError,
)
from satc_shared.review_process.models import ahora

from core.permission import Permission
from db.models import Expediente
from db.models.documento_proceso import (
    MODELOS_DOCUMENTO,
    DocumentoProceso,
    DocumentoProcesoRevision,
)
import services.docs as docs_svc
import services.notification as notif_svc
import services.users as users_svc

logger = logging.getLogger(__name__)

APROBADO_FIRMA = "aprobado_firma"
# app-users guarda ``notificacion.tipo`` en String(15): no superar 15 caracteres.
TIPO_NOTIFICACION = "recurso_doc"
EXTENSION_PDF = (".pdf",)
MAX_BYTES_ARCHIVO = 50 * 1024 * 1024  # tope defensivo; app-docs aplica su propio límite

# TODO(negocio): el plan no define tope de devoluciones y no hay reasignación.
# Un valor muy alto equivale a "sin límite" sin tocar el paquete compartido.
MAX_DEVOLUCIONES = 9999

ESTADOS_POR_SUBIR = (PENDIENTE_CARGA, RECHAZADO, APROBADO_FIRMA)
ESTADOS_FINALES = (APROBADO, FINALIZADO)


# ════════════════════════════════════════════════════════════ catálogo

ETIQUETAS_PERMISO: dict[str, str] = {
    Permission.LIDER_JURIDICO: "Líder jurídico",
    Permission.LIDER_PROYECTO: "Líder del proyecto",
    Permission.ASESORA_SUBDIRECCION: "Asesora de subdirección",
    Permission.LIDER_TECNICO: "Líder técnico",
    Permission.SIG: "SIG",
}

ETIQUETAS_ETAPA: dict[str, str] = {
    "acto_admite": "Etapa 1 · Auto que admite",
    "concepto_tecnico": "Concepto técnico",
    "requerimiento": "Requerimiento",
    "decision": "Etapa 4 · Decisión",
    "recurso_reposicion": "Recurso de reposición",
    "memorias_calculo": "Etapa 5 · Memorias de cálculo",
    "recibo_satisfaccion_obras": "Etapa 6 · Recibo a satisfacción de obras",
    "expediente_involucrado": "Tercero interviniente",
}


@dataclass(frozen=True)
class Cadena:
    """Cadena de revisión de un ``tipo_documento``.

    ``pasos``: tupla ordenada de pasos; cada paso es una tupla de permisos que
    deben revisar todos (en cualquier orden). El orden dentro del paso solo fija
    cuál permiso se usa primero si un usuario tiene varios."""

    tipo_documento: str
    etiqueta: str
    etapa_tipo: str
    pasos: tuple[tuple[str, ...], ...]

    @property
    def permisos(self) -> frozenset[str]:
        return frozenset(p for paso in self.pasos for p in paso)

    def permisos_paso(self, indice: int) -> tuple[str, ...]:
        return self.pasos[indice] if 0 <= indice < len(self.pasos) else ()

    def es_ultimo(self, indice: int) -> bool:
        return indice >= len(self.pasos) - 1


_J, _P, _A = Permission.LIDER_JURIDICO, Permission.LIDER_PROYECTO, Permission.ASESORA_SUBDIRECCION
_T, _S = Permission.LIDER_TECNICO, Permission.SIG

_JURIDICA_ESTANDAR = ((_J,), (_P,))           # líder jurídico → líder del proyecto
_JURIDICA_DECISION = ((_J,), (_P, _A))        # → líder del proyecto Y asesora
_SOLO_LIDER_TECNICO = ((_T,),)

# ÚNICO lugar donde se configuran las cadenas (DISENO_TECNICO §4).
CADENAS: dict[str, Cadena] = {c.tipo_documento: c for c in (
    Cadena("AUTO_ADMITE", "Auto que admite", "acto_admite", _JURIDICA_ESTANDAR),
    Cadena("REQUERIMIENTO", "Requerimiento", "requerimiento", _JURIDICA_ESTANDAR),
    Cadena("APRUEBA_MEMORIAS", "Acto que aprueba las memorias", "memorias_calculo", _JURIDICA_ESTANDAR),
    Cadena("DECISION", "Decisión", "decision", _JURIDICA_DECISION),
    Cadena("RECURSO", "Acto que resuelve el recurso", "recurso_reposicion", _JURIDICA_DECISION),
    # TODO(negocio): el plan no dice quién revisa el acto que reconoce al tercero
    # interviniente. Provisional: igual que el auto admite.
    Cadena("RECONOCE_TERCERO", "Acto que reconoce al tercero interviniente", "expediente_involucrado",
           _JURIDICA_ESTANDAR),
    # TODO(negocio): quién revisa el acto que aprueba la obra (plan §4-Etapa 6 y §9).
    # Provisional: igual que el auto admite.
    Cadena("APRUEBA_OBRAS", "Acto que aprueba las obras", "recibo_satisfaccion_obras", _JURIDICA_ESTANDAR),
    Cadena("CONCEPTO_ETAPA2", "Concepto técnico (etapa 2)", "concepto_tecnico", ((_T, _S), (_P,))),
    Cadena("CONCEPTO_ADICIONAL", "Concepto técnico adicional", "concepto_tecnico", _SOLO_LIDER_TECNICO),
    Cadena("CONCEPTO_MEMORIAS", "Concepto técnico de memorias", "concepto_tecnico", _SOLO_LIDER_TECNICO),
    Cadena("CONCEPTO_SUBSANACION", "Concepto técnico de la subsanación", "concepto_tecnico", _SOLO_LIDER_TECNICO),
    Cadena("CONCEPTO_OBRAS", "Concepto técnico de obras", "concepto_tecnico", _SOLO_LIDER_TECNICO),
    Cadena("CONCEPTO_OBRAS_SEGUNDO", "Segundo concepto técnico de obras", "concepto_tecnico", _SOLO_LIDER_TECNICO),
)}

PERMISOS_REVISOR: tuple[str, ...] = tuple(Permission.REVISORES)


def cadena_de(tipo_documento: str) -> Cadena:
    cadena = CADENAS.get(tipo_documento)
    if cadena is None:
        raise ValidacionError(f"Tipo de documento desconocido: {tipo_documento}")
    return cadena


def etiqueta_permiso(permiso: str) -> str:
    return ETIQUETAS_PERMISO.get(permiso, permiso)


def etiqueta_tipo_documento(tipo_documento: str) -> str:
    cadena = CADENAS.get(tipo_documento)
    return cadena.etiqueta if cadena else tipo_documento


def etiqueta_etapa(etapa_tipo: str) -> str:
    return ETIQUETAS_ETAPA.get(etapa_tipo, etapa_tipo)


def _permisos_info(permisos: Iterable[str]) -> list[dict]:
    return [{"permiso": p, "etiqueta": etiqueta_permiso(p)} for p in permisos]


# ════════════════════════════════════════════════════════ permisos usuario

async def permisos_de_usuario(user_id: int, permisos: Iterable[str] = PERMISOS_REVISOR) -> frozenset[str]:
    """Subconjunto de ``permisos`` que tiene el usuario (consultas en paralelo,
    cacheadas por ``services.users``). Para listados: resolver UNA vez por
    petición y pasar el resultado (sin N+1 a app-users)."""
    permisos = tuple(dict.fromkeys(permisos))
    if not permisos:
        return frozenset()
    resultados = await asyncio.gather(*(users_svc.verify_permission(user_id, p) for p in permisos))
    return frozenset(p for p, ok in zip(permisos, resultados) if ok)


class Conflicto(ReviewError):
    """El documento cambió mientras el usuario lo veía (otro revisor ya revisó,
    cambió de paso o de estado): recargar."""

    status_code = 409


class ProcesoYaExiste(ReviewError):
    status_code = 409


# ════════════════════════════════════════════════════════════════ flujo

async def _revisados_en_paso(db: AsyncSession, proceso_id: int, paso: int) -> dict[str, DocumentoProcesoRevision]:
    """Permisos que ya revisaron (aprobaron, aprobaron para firma o devolvieron)
    en ``paso`` → revisión más antigua con ese permiso."""
    filas = (await db.execute(
        select(DocumentoProcesoRevision)
        .where(
            DocumentoProcesoRevision.proceso_id == proceso_id,
            DocumentoProcesoRevision.paso == paso,
            DocumentoProcesoRevision.permiso.is_not(None),
        )
        .order_by(DocumentoProcesoRevision.fecha_revision, DocumentoProcesoRevision.id)
    )).scalars().all()
    revisados: dict[str, DocumentoProcesoRevision] = {}
    for r in filas:
        revisados.setdefault(r.permiso, r)
    return revisados


class FlujoDocumento(FlujoRevision):
    """Máquina de estados del documento (DISENO_TECNICO §4).

    ``pendiente_carga → en_revision → (aprobación parcial: sigue en_revision /
    avanza de paso) → aprobado_firma → [versión firmada PDF] → aprobado``;
    ``devuelto → rechazado → [nueva versión] → en_revision`` (mismo paso)."""

    ESTADOS_EXTRA = (Estado(APROBADO_FIRMA, "Aprobado para firma", "warning"),)
    ACCIONES_EXTRA = (
        Accion(
            APROBADO_FIRMA, "Aprobar para firma",
            etiqueta_realizada="Aprobado para firma", tono="success",
            estado_destino=APROBADO_FIRMA, auditoria="aprobar_firma", icono="firmar",
        ),
    )
    EVENTOS_AUDITORIA_EXTRA = (
        EventoAuditoria("aprobar_paso", "Aprobado (paso completado)", "success"),
        EventoAuditoria("avanzar_paso", "Pasa al siguiente paso de revisión", "info"),
        EventoAuditoria("aprobar_firma_automatico", "Aprobado para firma (sin revisores pendientes)", "success"),
        EventoAuditoria("cerrar", "Proceso cerrado", "neutral"),
        EventoAuditoria("reasignar", "Encargado reasignado", "info"),
    )
    # rechazado: corrección; aprobado_firma: versión firmada (solo vía cargar_version_final).
    estados_subida = frozenset({RECHAZADO, APROBADO_FIRMA})
    max_devoluciones = MAX_DEVOLUCIONES

    # ------------------------------------------------------------- cadena
    @staticmethod
    def cadena(proceso: DocumentoProceso) -> Cadena:
        return cadena_de(proceso.tipo_documento)

    async def permisos_usuario(self, ctx: Contexto, user_id: int) -> frozenset[str]:
        """Permisos de revisor de la cadena que tiene el usuario (cacheado en ctx)."""
        cache = ctx.__dict__.setdefault("_permisos_usuario", {})
        if user_id not in cache:
            cache[user_id] = await permisos_de_usuario(user_id, sorted(self.cadena(ctx.proceso).permisos))
        return cache[user_id]

    async def revisados_paso_actual(self, ctx: Contexto) -> dict[str, DocumentoProcesoRevision]:
        return await _revisados_en_paso(ctx.db, ctx.proceso.id, ctx.proceso.paso_actual or 0)

    async def pendientes_paso(self, ctx: Contexto) -> list[str]:
        """Permisos del paso actual que aún no revisaron (en orden de la cadena)."""
        p = ctx.proceso
        revisados = await self.revisados_paso_actual(ctx)
        return [perm for perm in self.cadena(p).permisos_paso(p.paso_actual or 0) if perm not in revisados]

    async def permiso_para_revisar(self, ctx: Contexto, user_id: int) -> str | None:
        """Primer permiso pendiente del paso actual que tiene el usuario (o None)."""
        mios = await self.permisos_usuario(ctx, user_id)
        for perm in await self.pendientes_paso(ctx):
            if perm in mios:
                return perm
        return None

    # ----------------------------------------------------------- permisos
    async def puede_ver(self, ctx: Contexto, user_id: int) -> bool:
        if ctx.proceso.creador_id == user_id:
            return True
        if await self.permisos_usuario(ctx, user_id):
            return True
        lectura = await permisos_de_usuario(
            user_id, (Permission.CONSULT, Permission.MANAGE, Permission.SUPER_MANAGE)
        )
        return bool(lectura)

    async def puede_revisar(self, ctx: Contexto, user_id: int) -> bool:
        p = ctx.proceso
        if not p.activo or p.estado != EN_REVISION:
            return False
        return await self.permiso_para_revisar(ctx, user_id) is not None

    async def puede_subir_version(self, ctx: Contexto, user_id: int) -> bool:
        # Encargado = creador del proceso (abogado o técnico seleccionado), y
        # además conserva el permiso que lo habilitó (V1 actos / V3 conceptos):
        # si se lo quitan después de asignarse, deja de poder proyectar.
        if ctx.proceso.creador_id != user_id:
            return False
        return bool(await permisos_de_usuario(user_id, permisos_encargado(ctx.proceso.etapa_tipo)))

    # ------------------------------------------------------- validaciones
    def extensiones_subida(self, proceso) -> tuple[str, ...]:
        if proceso.estado == APROBADO_FIRMA:
            return EXTENSION_PDF
        return super().extensiones_subida(proceso)

    async def validar_accion(self, ctx: Contexto, accion: Accion, user_id: int) -> str | None:
        motivo = await super().validar_accion(ctx, accion, user_id)
        if motivo or accion.codigo != APROBADO_FIRMA:
            return motivo
        if not await self.cierra_cadena(ctx, user_id):
            return "Solo se aprueba para firma en el último paso, cuando eres el último revisor pendiente"
        return None

    async def cierra_cadena(self, ctx: Contexto, user_id: int) -> bool:
        """Si la aprobación de este usuario completa el último paso."""
        p = ctx.proceso
        permiso = await self.permiso_para_revisar(ctx, user_id)
        if permiso is None or not self.cadena(p).es_ultimo(p.paso_actual or 0):
            return False
        return await self.pendientes_paso(ctx) == [permiso]

    # ------------------------------------------------------- transiciones
    def estado_tras_accion(self, proceso, accion: Accion) -> str:
        if accion.cuenta_devolucion:
            return RECHAZADO  # sin tope (TODO(negocio)): nunca finaliza por devoluciones
        return super().estado_tras_accion(proceso, accion)

    async def avanzar_si_completo(self, ctx: Contexto, user_id: int | None) -> str:
        """Tras una corrección: si el paso actual ya no tiene permisos pendientes
        (todos aprobaron o devolvieron antes) avanza; si era el último, queda
        ``aprobado_firma``. Devuelve el estado resultante."""
        p = ctx.proceso
        cadena = self.cadena(p)
        while not await self.pendientes_paso(ctx):
            if cadena.es_ultimo(p.paso_actual or 0):
                ctx.auditar(
                    "aprobar_firma_automatico", user_id,
                    "Todos los revisores del último paso ya revisaron: aprobado para firma",
                    {"paso": (p.paso_actual or 0) + 1},
                )
                return APROBADO_FIRMA
            p.paso_actual = (p.paso_actual or 0) + 1
            ctx.auditar(
                "avanzar_paso", user_id,
                f"Sin revisores pendientes en el paso: pasa al paso {p.paso_actual + 1}",
                {"paso": p.paso_actual + 1, "permisos": list(cadena.permisos_paso(p.paso_actual))},
            )
        return EN_REVISION

    async def despues_de_subida(self, ctx: Contexto, version, user_id: int, estado_anterior: str) -> str:
        if estado_anterior == APROBADO_FIRMA:
            revisor = await ctx.ultimo_revisor(APROBADO_FIRMA)
            await ctx.registrar_revision(
                accion=APROBADO,
                revisor_id=revisor or user_id,
                comentarios="Auto-aprobado: versión firmada cargada tras la aprobación para firma",
            )
            ctx.auditar("aprobar", user_id, f"Versión firmada auto-aprobada (v{version.numero_version})")
            return APROBADO
        if estado_anterior == RECHAZADO:
            # Vuelve al MISMO paso; quien devolvió ya cuenta como revisado (plan §5.2).
            return await self.avanzar_si_completo(ctx, user_id)
        return EN_REVISION


FLUJO = FlujoDocumento()


@dataclass
class ResultadoRevisionDocumento(ResultadoRevision):
    permiso: str = ""
    paso_anterior: int = 0
    paso_nuevo: int = 0

    @property
    def avanzo_paso(self) -> bool:
        return self.paso_nuevo != self.paso_anterior


class ServicioDocumento(ProcesoRevisionService):
    """``ProcesoRevisionService`` con revisión por pasos/permisos."""

    # ---------------------------------------------------------- revisar
    async def revisar(
        self,
        db: AsyncSession,
        proceso_id: int,
        *,
        user_id: int,
        accion: str,
        comentario: str | None = None,
        adjunto: ArchivoRef | None = None,
    ) -> ResultadoRevisionDocumento:
        """Revisa con el primer permiso pendiente del paso actual que tenga el
        usuario. 403 si no tiene ningún permiso de la cadena; 409 si ya revisó
        con todos sus permisos, no es su paso o el proceso cambió de estado."""
        flujo: FlujoDocumento = self.flujo  # type: ignore[assignment]
        ctx = await self.contexto(db, proceso_id, para_actualizar=True)
        p: DocumentoProceso = ctx.proceso
        cadena = flujo.cadena(p)

        mios = await flujo.permisos_usuario(ctx, user_id)
        if not mios:
            raise PermisoDenegado("No tienes un permiso de revisor para este documento")
        acc = flujo.acciones.get(accion)
        if acc is None or accion not in (APROBADO, APROBADO_FIRMA, DEVUELTO):
            raise ValidacionError(f"Acción de revisión inválida: {accion}")
        if not p.activo:
            raise Conflicto("Este proceso de revisión ya no está vigente. Recarga")
        if p.estado != EN_REVISION:
            raise Conflicto(
                f"El documento ya no está en revisión (estado: {flujo.estado_info(p.estado).etiqueta}). Recarga"
            )
        permiso = await flujo.permiso_para_revisar(ctx, user_id)
        if permiso is None:
            raise Conflicto(await _motivo_sin_turno(flujo, ctx, mios))
        if acc.requiere_comentario and not (comentario or "").strip():
            raise ValidacionError("Esta acción requiere un comentario")
        if adjunto is not None:
            if not acc.admite_adjunto:
                raise ValidacionError("Esta acción no admite archivo adjunto")
            if not adjunto.tiene_extension(acc.adjunto_extensiones):
                raise ValidacionError(f"Formato no permitido. Permitidos: {', '.join(acc.adjunto_extensiones)}")
        motivo = await flujo.validar_accion(ctx, acc, user_id)
        if motivo:
            raise ValidacionError(motivo)

        estado_anterior = p.estado
        paso_anterior = p.paso_actual or 0
        pendientes = await flujo.pendientes_paso(ctx)
        completa_paso = pendientes == [permiso]

        if acc.cuenta_devolucion:
            codigo = DEVUELTO
            p.numero_devoluciones = (p.numero_devoluciones or 0) + 1
            estado_nuevo = flujo.estado_tras_accion(p, acc)
        elif completa_paso and cadena.es_ultimo(paso_anterior):
            codigo, estado_nuevo = APROBADO_FIRMA, APROBADO_FIRMA
        else:
            codigo, estado_nuevo = APROBADO, EN_REVISION
            if completa_paso:
                p.paso_actual = paso_anterior + 1

        revision = await self._registrar_revision(ctx, codigo, user_id, comentario, adjunto)
        revision.paso = paso_anterior
        revision.permiso = permiso
        p.estado = estado_nuevo
        p.fecha_ultima_actualizacion = ahora()

        acc_real = flujo.acciones[codigo]
        if codigo == APROBADO and completa_paso:
            cod_aud = "aprobar_paso"
            descripcion = (
                f"Aprobado por {etiqueta_permiso(permiso)}: paso {paso_anterior + 1} completo, "
                f"pasa al paso {p.paso_actual + 1}"
            )
        elif codigo == APROBADO:
            faltan = [etiqueta_permiso(x) for x in pendientes if x != permiso]
            cod_aud = acc_real.codigo_auditoria
            descripcion = f"Aprobado por {etiqueta_permiso(permiso)}; faltan en el paso: {', '.join(faltan)}"
        elif codigo == APROBADO_FIRMA:
            cod_aud = acc_real.codigo_auditoria
            descripcion = f"Aprobado para firma por {etiqueta_permiso(permiso)}"
        else:
            cod_aud = acc_real.codigo_auditoria
            descripcion = f"Devuelto por {etiqueta_permiso(permiso)} (devolución {p.numero_devoluciones})"
        self._auditar(db, p, cod_aud, user_id, descripcion, {
            "comentarios": comentario,
            "version": p.version_actual,
            "adjunto": adjunto.nombre if adjunto else None,
            "estado_anterior": estado_anterior,
            "paso": paso_anterior + 1,
            "permiso": permiso,
        })
        await db.flush()
        if adjunto is not None and adjunto.file_id:
            await self._incrementar_usos([adjunto.file_id])

        return ResultadoRevisionDocumento(
            p, revision, acc_real, estado_anterior, estado_nuevo, descripcion,
            permiso=permiso, paso_anterior=paso_anterior, paso_nuevo=p.paso_actual or 0,
        )

    # ------------------------------------------------- acciones por usuario
    async def acciones_disponibles(self, ctx: Contexto, user_id: int) -> list[AccionRevision]:
        flujo: FlujoDocumento = self.flujo  # type: ignore[assignment]
        p = ctx.proceso
        if not p.activo or p.estado != EN_REVISION:
            return []
        mios = await flujo.permisos_usuario(ctx, user_id)
        if not mios:
            return []
        cadena = flujo.cadena(p)
        paso = p.paso_actual or 0
        permiso = await flujo.permiso_para_revisar(ctx, user_id)
        if permiso is not None:
            aprobar = APROBADO_FIRMA if await flujo.cierra_cadena(ctx, user_id) else APROBADO
            acciones = []
            for codigo in (aprobar, DEVUELTO):
                acc = flujo.acciones[codigo]
                acciones.append(flujo.accion_regla(acc, await flujo.validar_accion(ctx, acc, user_id)))
            return acciones
        # Tiene permiso de la cadena pero no le toca: se muestran bloqueadas con el motivo.
        en_paso_actual = mios & set(cadena.permisos_paso(paso))
        posteriores = mios & {x for i in range(paso + 1, len(cadena.pasos)) for x in cadena.pasos[i]}
        if not en_paso_actual and not posteriores:
            return []  # solo revisaba pasos anteriores: ya cumplió
        motivo = await _motivo_sin_turno(flujo, ctx, mios)
        return [flujo.accion_regla(flujo.acciones[c], motivo) for c in (APROBADO, DEVUELTO)]

    async def subida_version(self, ctx: Contexto, user_id: int) -> SubidaVersion | None:
        if not await self.flujo.puede_subir_version(ctx, user_id):
            return None
        p = ctx.proceso
        if not p.activo:
            return SubidaVersion(permitida=False, extensiones=[], motivo="Este proceso ya no está vigente")
        if p.estado == APROBADO_FIRMA:
            return SubidaVersion(
                permitida=False,
                extensiones=list(EXTENSION_PDF),
                motivo=MOTIVO_VERSION_FINAL,
            )
        if p.estado == EN_REVISION:
            return SubidaVersion(
                permitida=False,
                extensiones=list(self.flujo.extensiones_subida(p)),
                motivo="El documento está en revisión; podrás subir una nueva versión si te lo devuelven",
            )
        return await super().subida_version(ctx, user_id)


MOTIVO_VERSION_FINAL = (
    "Aprobado para firma: carga la versión firmada (PDF) y sus datos desde la etapa, "
    "con \"Cargar versión final\""
)


async def _motivo_sin_turno(flujo: FlujoDocumento, ctx: Contexto, mios: frozenset[str]) -> str:
    p = ctx.proceso
    cadena = flujo.cadena(p)
    paso = p.paso_actual or 0
    pendientes = await flujo.pendientes_paso(ctx)
    faltan = ", ".join(etiqueta_permiso(x) for x in pendientes) or "nadie"
    if mios & set(cadena.permisos_paso(paso)):
        return f"Ya revisaste este documento en el paso {paso + 1}. Pendiente de: {faltan}"
    if any(mios & set(cadena.pasos[i]) for i in range(paso + 1, len(cadena.pasos))):
        return f"Aún no es tu turno. Pendiente de: {faltan} (paso {paso + 1} de {len(cadena.pasos)})"
    return "Ya revisaste este documento. Recarga"


def servicio() -> ServicioDocumento:
    # files_client se resuelve en cada llamada para que los tests puedan sustituirlo.
    return ServicioDocumento(MODELOS_DOCUMENTO, FLUJO, files=docs_svc.files_client)


def http_error(e: ReviewError) -> HTTPException:
    return HTTPException(status_code=e.status_code, detail=e.detail)


# ══════════════════════════════════════════════════════════ notificaciones

@dataclass
class Avisos:
    """Notificaciones a app-users pendientes de enviar DESPUÉS del commit
    (best-effort: nunca abortan la operación). ``tipo="recurso_doc"``,
    ``id_vinculada = str(documento_proceso.id)`` (el front abre Mis informes).

    ``agregar(usuario_id, mensaje, proceso_id=...)`` a un usuario concreto;
    ``agregar_permiso(permiso, mensaje, proceso_id=...)`` a todos los usuarios
    con ese permiso (se resuelven al enviar, no dentro de la transacción)."""

    items: list[tuple[int, str, int]] = field(default_factory=list)
    por_permiso: list[tuple[str, str, int, frozenset[int]]] = field(default_factory=list)

    def agregar(self, usuario_id: Optional[int], mensaje: str, *, proceso_id: int) -> None:
        item = (int(usuario_id), mensaje, int(proceso_id)) if usuario_id else None
        if item and item not in self.items:
            self.items.append(item)

    def agregar_permiso(self, permiso: str, mensaje: str, *, proceso_id: int, excluir: Iterable[int] = ()) -> None:
        self.por_permiso.append((permiso, mensaje, int(proceso_id), frozenset(int(x) for x in excluir)))

    async def enviar(self) -> None:
        destinos = list(self.items)
        for permiso, mensaje, proceso_id, excluir in self.por_permiso:
            try:
                usuarios = await users_svc.get_users_by_permission(permiso)
            except Exception as e:  # pragma: no cover - el wrapper ya no lanza
                logger.warning(f"No se pudieron resolver usuarios con {permiso}: {e}")
                continue
            for uid in usuarios or {}:
                item = (int(uid), mensaje, proceso_id)
                if int(uid) not in excluir and item not in destinos:
                    destinos.append(item)
        for usuario_id, mensaje, proceso_id in destinos:
            try:
                resultado = await notif_svc.create_notification(
                    mensaje=mensaje, id_vinculada=str(proceso_id), tipo=TIPO_NOTIFICACION, usuario_id=usuario_id,
                )
                if not resultado.get("ok"):
                    logger.warning(f"Notificación del documento {proceso_id} a {usuario_id} falló: {resultado}")
            except Exception as e:  # pragma: no cover
                logger.warning(f"Notificación del documento {proceso_id} a {usuario_id} falló: {e}")


async def datos_expediente(db: AsyncSession, expediente_id: int) -> tuple[Optional[str], Optional[str]]:
    """(radicado, código CA) del expediente."""
    fila = (await db.execute(
        select(Expediente.radicado, Expediente.expediente).where(Expediente.id == expediente_id)
    )).first()
    return (fila[0], fila[1]) if fila else (None, None)


async def _encabezado(db: AsyncSession, proceso: DocumentoProceso) -> str:
    radicado, codigo = await datos_expediente(db, proceso.expediente_id)
    ident = codigo or radicado or str(proceso.expediente_id)
    return f"Expediente {ident}\n{etiqueta_tipo_documento(proceso.tipo_documento)}"


def _avisar_pendientes(avisos: Avisos, proceso: DocumentoProceso, pendientes: Iterable[str], mensaje: str) -> None:
    for permiso in pendientes:
        avisos.agregar_permiso(permiso, mensaje, proceso_id=proceso.id, excluir=(proceso.creador_id,))


async def avisos_tras_revision(db: AsyncSession, avisos: Avisos, res: ResultadoRevisionDocumento) -> None:
    """DISENO §4.7: a los permisos del paso que queda pendiente cuando avanza; al
    encargado cuando devuelven o aprueban para firma."""
    p = res.proceso
    enc = await _encabezado(db, p)
    if res.estado_nuevo == RECHAZADO:
        con_adj = ", con documento de observaciones" if res.revision.adjunto_url else ""
        avisos.agregar(p.creador_id, f"{enc}: devuelto por {etiqueta_permiso(res.permiso)}{con_adj}", proceso_id=p.id)
    elif res.estado_nuevo == APROBADO_FIRMA:
        avisos.agregar(
            p.creador_id, f"{enc}: aprobado para firma, carga la versión firmada en PDF desde la etapa",
            proceso_id=p.id,
        )
    elif res.estado_nuevo == EN_REVISION and res.avanzo_paso:
        ctx = await servicio().contexto(db, p.id)
        _avisar_pendientes(avisos, p, await FLUJO.pendientes_paso(ctx), f"{enc}: pendiente de tu revisión")


async def avisos_tras_version(db: AsyncSession, avisos: Avisos, res: ResultadoVersion) -> None:
    p = res.proceso
    enc = await _encabezado(db, p)
    if res.estado_nuevo == EN_REVISION:
        ctx = await servicio().contexto(db, p.id)
        _avisar_pendientes(
            avisos, p, await FLUJO.pendientes_paso(ctx),
            f"{enc}: nueva versión (v{res.version.numero_version}) pendiente de tu revisión",
        )
    elif res.estado_nuevo == APROBADO_FIRMA:
        avisos.agregar(
            p.creador_id,
            f"{enc}: sin revisores pendientes, aprobado para firma. Carga la versión firmada desde la etapa",
            proceso_id=p.id,
        )


# ══════════════════════════════════════════════════════════ API para C

async def crear_proceso(
    db: AsyncSession,
    *,
    expediente_id: int,
    tipo_documento: str,
    etapa_tipo: str,
    etapa_ref_id: int,
    encargado_id: int,
    usuario_id: int,
    avisos: Avisos,
) -> DocumentoProceso:
    """Crea el proceso vigente de una fila de etapa en ``pendiente_carga``
    (al asignarse el abogado o al seleccionar el técnico).

    - ``tipo_documento``: clave de ``CADENAS``; su ``etapa_tipo`` debe coincidir.
    - ``encargado_id``: quien proyecta y sube (queda como ``creador_id``).
    - ``usuario_id``: quien ejecuta (p. ej. el abogado que selecciona al técnico).
    - Avisa al encargado (tras el commit, con ``avisos.enviar()``).

    Lanza ``ValidacionError`` (400) si el tipo no existe o no corresponde a la
    etapa y ``ProcesoYaExiste`` (409) si la etapa ya tiene proceso vigente. Si
    dos peticiones crean a la vez, el índice único parcial hace fallar el flush
    con ``IntegrityError``: envolver en ``integridad_a_409``. No hace commit."""
    cadena = cadena_de(tipo_documento)
    if cadena.etapa_tipo != etapa_tipo:
        raise ValidacionError(
            f"El tipo de documento {tipo_documento} corresponde a la etapa {cadena.etapa_tipo}, no a {etapa_tipo}"
        )
    if await proceso_vigente(db, etapa_tipo, etapa_ref_id) is not None:
        raise ProcesoYaExiste("Esta etapa ya tiene un proceso de revisión vigente")
    radicado, codigo = await datos_expediente(db, expediente_id)
    if radicado is None:
        raise ValidacionError("Expediente no encontrado")
    nombre = f"{cadena.etiqueta} - Expediente {codigo or radicado}"
    proceso = DocumentoProceso(
        nombre=nombre[:255],
        descripcion=f"{etiqueta_etapa(etapa_tipo)}. Encargado del cargue y las correcciones.",
        creador_id=encargado_id,
        estado=PENDIENTE_CARGA,
        version_actual=0,
        numero_devoluciones=0,
        expediente_id=expediente_id,
        tipo_documento=tipo_documento,
        etapa_tipo=etapa_tipo,
        etapa_ref_id=etapa_ref_id,
        paso_actual=0,
        activo=True,
    )
    db.add(proceso)
    await db.flush()
    servicio()._auditar(db, proceso, "crear", usuario_id, f"Proceso creado: {nombre}", {
        "tipo_documento": tipo_documento, "etapa_tipo": etapa_tipo, "etapa_ref_id": etapa_ref_id,
        "encargado_id": encargado_id,
    })
    await db.flush()
    avisos.agregar(
        encargado_id,
        f"Expediente {codigo or radicado}\n{cadena.etiqueta}: asignado, proyecta y sube el documento",
        proceso_id=proceso.id,
    )
    return proceso


def permisos_encargado(etapa_tipo: str) -> tuple[str, ...]:
    """Permisos (basta uno) que debe tener el encargado para proyectar: técnico
    en los conceptos (V3); gestión o super gestión en los actos (V1)."""
    if etapa_tipo == "concepto_tecnico":
        return (Permission.TECNICO,)
    return (Permission.MANAGE, Permission.SUPER_MANAGE)


async def reasignar_encargado(
    db: AsyncSession, proceso: DocumentoProceso, encargado_id: int, *, usuario_id: int, avisos: Avisos,
    descripcion: str = "Encargado reasignado",
) -> bool:
    """Cambia el encargado (``creador_id``) del proceso vigente cuando la fila
    de etapa cambia de abogado/técnico (p. ej. super gestión), para que el nuevo
    encargado pueda subir versiones y cargar la versión final. No toca procesos
    inactivos o en estado final. Audita y avisa al nuevo encargado. Devuelve si
    hubo cambio. No hace commit."""
    if not proceso.activo or proceso.estado in ESTADOS_FINALES or proceso.creador_id == encargado_id:
        return False
    anterior = proceso.creador_id
    proceso.creador_id = encargado_id
    proceso.fecha_ultima_actualizacion = ahora()
    servicio()._auditar(db, proceso, "reasignar", usuario_id, descripcion, {
        "encargado_anterior": anterior, "encargado_nuevo": encargado_id,
    })
    await db.flush()
    avisos.agregar(
        encargado_id,
        f"{await _encabezado(db, proceso)}: te reasignaron como encargado, proyecta y sube el documento",
        proceso_id=proceso.id,
    )
    return True


async def proceso_vigente(
    db: AsyncSession, etapa_tipo: str, etapa_ref_id: int, para_actualizar: bool = False
) -> Optional[DocumentoProceso]:
    """Proceso activo de la fila de etapa (o None). ``para_actualizar`` lo
    bloquea (``FOR UPDATE``); bloquear ANTES el expediente (``bloquear_expediente``)
    para respetar el orden de bloqueos de las rutas de revisión."""
    stmt = select(DocumentoProceso).where(
        DocumentoProceso.etapa_tipo == etapa_tipo,
        DocumentoProceso.etapa_ref_id == etapa_ref_id,
        DocumentoProceso.activo.is_(True),
    )
    if para_actualizar:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    return await db.scalar(stmt)


async def procesos_vigentes(
    db: AsyncSession, pares: Iterable[tuple[str, int]]
) -> dict[tuple[str, int], DocumentoProceso]:
    """Batch de ``proceso_vigente`` para el árbol de etapas: {(etapa_tipo, id): proceso}."""
    pares = {(t, int(i)) for t, i in pares if i is not None}
    if not pares:
        return {}
    ids_por_tipo: dict[str, set[int]] = {}
    for t, i in pares:
        ids_por_tipo.setdefault(t, set()).add(i)
    resultado: dict[tuple[str, int], DocumentoProceso] = {}
    for tipo, ids in ids_por_tipo.items():
        filas = (await db.execute(select(DocumentoProceso).where(
            DocumentoProceso.etapa_tipo == tipo,
            DocumentoProceso.etapa_ref_id.in_(ids),
            DocumentoProceso.activo.is_(True),
        ))).scalars().all()
        resultado.update({(f.etapa_tipo, f.etapa_ref_id): f for f in filas})
    return resultado


async def cargar_version_final(
    db: AsyncSession,
    proceso: DocumentoProceso,
    archivo: ArchivoRef,
    user_id: int,
    avisos: Avisos,
    comentario: str | None = "Versión final firmada",
) -> ResultadoVersion:
    """Carga la versión firmada: valida estado ``aprobado_firma``, PDF y que
    ``user_id`` sea el encargado; registra la versión (incrementa ``numero_usos``
    del archivo) y deja el proceso ``aprobado``. La usa C dentro de SU
    transacción, junto con la creación del acto (``services.actos.crear_acto``)
    o el llenado del concepto. Re-bloquea el proceso (``FOR UPDATE``). No hace
    commit. Errores: 403 (no encargado), 409 (no está en aprobado_firma / no
    vigente), 400 (no PDF), 502 (app-docs no registró el uso)."""
    svc = servicio()
    ctx = await svc.contexto(db, proceso.id, para_actualizar=True)
    p = ctx.proceso
    if not p.activo:
        raise Conflicto("Este proceso de revisión ya no está vigente. Recarga")
    if p.creador_id != user_id:
        raise PermisoDenegado("Solo el encargado puede cargar la versión final")
    if p.estado != APROBADO_FIRMA:
        raise Conflicto(
            "El documento aún no está aprobado para firma "
            f"(estado: {FLUJO.estado_info(p.estado).etiqueta}). Recarga"
        )
    if not archivo.tiene_extension(EXTENSION_PDF):
        raise ValidacionError("La versión final firmada debe ser un PDF")
    res = await svc._agregar_version(ctx, archivo, user_id, comentario)
    enc = await _encabezado(db, p)
    revisor = await ctx.ultimo_revisor(APROBADO_FIRMA)
    if revisor and revisor != user_id:
        avisos.agregar(revisor, f"{enc}: versión firmada cargada, documento aprobado", proceso_id=p.id)
    return res


async def cerrar_proceso_vigente(
    db: AsyncSession, etapa_tipo: str, etapa_ref_id: int, *, usuario_id: int | None, descripcion: str
) -> Optional[DocumentoProceso]:
    """Finaliza (si no es final) y desactiva el proceso vigente de la etapa
    (p. ej. super gestión carga directo o se borra la etapa). Devuelve el
    proceso o None. No hace commit."""
    proceso = await proceso_vigente(db, etapa_tipo, etapa_ref_id, para_actualizar=True)
    if proceso is None:
        return None
    svc = servicio()
    if proceso.estado not in ESTADOS_FINALES:
        await svc.finalizar(db, proceso.id, usuario_id=usuario_id, descripcion=descripcion)
    else:
        svc._auditar(db, proceso, "cerrar", usuario_id, descripcion)
    proceso.activo = False
    await db.flush()
    return proceso


async def resumenes_procesos(
    db: AsyncSession,
    procesos: Iterable[DocumentoProceso],
    user_id: int,
    permisos_usuario: Optional[Iterable[str]] = None,
) -> dict[int, dict]:
    """``resumen_proceso`` en lote ({proceso_id: resumen}) con UNA consulta de
    revisiones. ``permisos_usuario``: resultado de ``permisos_de_usuario`` (si
    es None se resuelve aquí una sola vez)."""
    procesos = list(procesos)
    if not procesos:
        return {}
    mios = frozenset(permisos_usuario) if permisos_usuario is not None else await permisos_de_usuario(user_id)
    filas = (await db.execute(
        select(DocumentoProcesoRevision.proceso_id, DocumentoProcesoRevision.paso, DocumentoProcesoRevision.permiso)
        .where(
            DocumentoProcesoRevision.proceso_id.in_([p.id for p in procesos]),
            DocumentoProcesoRevision.permiso.is_not(None),
        )
    )).all()
    revisados: dict[tuple[int, int], set[str]] = {}
    for pid, paso, permiso in filas:
        revisados.setdefault((pid, paso), set()).add(permiso)
    return {p.id: _resumen(p, user_id, mios, revisados.get((p.id, p.paso_actual or 0), set())) for p in procesos}


def _resumen(p: DocumentoProceso, user_id: int, mios: frozenset[str], revisados: set[str]) -> dict:
    cadena = CADENAS.get(p.tipo_documento)
    paso = p.paso_actual or 0
    pendientes = (
        [x for x in cadena.permisos_paso(paso) if x not in revisados]
        if cadena and p.estado == EN_REVISION else []
    )
    soy_encargado = p.creador_id == user_id
    puedo_revisar = bool(p.activo and set(pendientes) & mios)
    requiere = bool(p.activo) and (
        (soy_encargado and p.estado in ESTADOS_POR_SUBIR) or puedo_revisar
    )
    return {
        "proceso_id": p.id,
        "tipo_documento": p.tipo_documento,
        "tipo_documento_etiqueta": etiqueta_tipo_documento(p.tipo_documento),
        "estado_proceso": FLUJO.estado_info(p.estado).model_dump(),
        "proceso_activo": bool(p.activo) and p.estado not in ESTADOS_FINALES,
        "paso_actual": paso + 1 if cadena else None,
        "total_pasos": len(cadena.pasos) if cadena else 0,
        "permisos_pendientes": _permisos_info(pendientes),
        "numero_devoluciones": p.numero_devoluciones or 0,
        "version_actual": p.version_actual or 0,
        "encargado_id": p.creador_id,
        "soy_encargado": soy_encargado,
        "puedo_revisar": puedo_revisar,
        "requiere_mi_accion": requiere,
    }


RESUMEN_VACIO = {
    "proceso_id": None,
    "tipo_documento": None,
    "tipo_documento_etiqueta": None,
    "estado_proceso": None,
    "proceso_activo": False,
    "paso_actual": None,
    "total_pasos": 0,
    "permisos_pendientes": [],
    "numero_devoluciones": 0,
    "version_actual": 0,
    "encargado_id": None,
    "soy_encargado": False,
    "puedo_revisar": False,
    "requiere_mi_accion": False,
}


async def resumen_proceso(
    db: AsyncSession,
    proceso: Optional[DocumentoProceso],
    user_id: int,
    permisos_usuario: Optional[Iterable[str]] = None,
) -> dict:
    """Campos del proceso vigente para listados y para el payload de cada etapa:
    ``proceso_id``, ``estado_proceso`` {codigo, etiqueta, tono}, ``paso_actual``
    (1-based) / ``total_pasos``, ``permisos_pendientes`` [{permiso, etiqueta}],
    ``version_actual``, ``numero_devoluciones``, ``soy_encargado``,
    ``puedo_revisar``, ``requiere_mi_accion``. Con ``proceso=None`` devuelve
    ``RESUMEN_VACIO``."""
    if proceso is None:
        return dict(RESUMEN_VACIO)
    return (await resumenes_procesos(db, [proceso], user_id, permisos_usuario))[proceso.id]


# ═════════════════════════════════════════════════════════════ archivos

async def subir_a_docs(archivo: UploadFile) -> ArchivoRef:
    """Sube un ``UploadFile`` a app-docs (/files/upload: valida y pasa ClamAV) y
    devuelve la referencia. Igual que infraction. 400/413/502 como HTTPException."""
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


async def archivo_ref_por_id(file_id: int, nombre: str | None = None) -> ArchivoRef:
    """``ArchivoRef`` de un archivo que el front ya subió a app-docs (``file_id``).
    Si no llega ``nombre`` se deriva del content-type (``documento_<id>.pdf``).
    404 si app-docs no lo conoce."""
    info = await docs_svc.get_file_info(file_id)
    if not info.get("ok"):
        raise HTTPException(status_code=404, detail="Archivo no encontrado en el gestor documental")
    data = info["data"]
    if not nombre:
        ext = ".pdf" if (data.get("content_type") or "").lower() == "application/pdf" else ""
        nombre = f"documento_{file_id}{ext}"
    return ArchivoRef(file_id=file_id, url=data.get("file_url") or f"/files/{file_id}",
                      nombre=nombre, size=data.get("file_size"))


__all__ = [
    "APROBADO_FIRMA", "Avisos", "CADENAS", "Cadena", "Conflicto", "FLUJO", "FlujoDocumento",
    "MAX_DEVOLUCIONES", "ProcesoYaExiste", "RESUMEN_VACIO", "ResultadoRevisionDocumento",
    "ServicioDocumento", "TIPO_NOTIFICACION", "archivo_ref_por_id", "avisos_tras_revision",
    "avisos_tras_version", "cadena_de", "cargar_version_final", "cerrar_proceso_vigente",
    "crear_proceso", "datos_expediente", "permisos_encargado", "reasignar_encargado", "etiqueta_etapa", "etiqueta_permiso",
    "etiqueta_tipo_documento", "http_error", "permisos_de_usuario", "proceso_vigente",
    "procesos_vigentes", "resumen_proceso", "resumenes_procesos", "servicio", "subir_a_docs",
]
