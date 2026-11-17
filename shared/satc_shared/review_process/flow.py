"""Máquina de estados base del proceso de revisión, extensible por subclase.

Estados base:
    pendiente_carga  -> creado sin versión; el creador debe subir la primera.
    en_revision      -> hay una versión esperando a los revisores.
    aprobado         -> final.
    rechazado        -> devuelto; el creador puede subir nueva versión.
    finalizado       -> final, se alcanzó el máximo de devoluciones (o cierre forzado).

Acciones base (desde ``en_revision``):
    aprobado  -> aprobado
    devuelto  -> rechazado, o finalizado si numero_devoluciones >= max_devoluciones.
                 Único que admite adjunto (pdf/doc/docx) por defecto.

Subir versión: solo en ``pendiente_carga`` (primera) o en ``estados_subida``
(por defecto ``rechazado``); tras subir, ``despues_de_subida`` decide el estado
(por defecto ``en_revision``).

Puntos de extensión para la app (subclase):
    ESTADOS_EXTRA / ACCIONES_EXTRA          estados y acciones nuevos
    estados_subida, extensiones_version     dónde y qué se puede subir
    max_devoluciones                        (o por constructor)
    puede_ver / puede_revisar / puede_subir_version   permisos (o callables por constructor)
    validar_accion / validar_subida         reglas extra; devuelven el motivo de bloqueo o None
    accion_aplicable                        oculta acciones según el proceso
    estado_tras_accion / despues_de_subida  transiciones
    auditoria_accion                        código/descripcion de auditoría
    EVENTOS_AUDITORIA_EXTRA                 etiqueta/tono de códigos de auditoría propios
                                            (los de las acciones se derivan de ``Accion``)
"""
from __future__ import annotations

from dataclasses import KW_ONLY, dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Callable, ClassVar, Optional

from .schemas import AccionRevision, AdjuntoRegla, EstadoInfo, Tono

if TYPE_CHECKING:  # pragma: no cover
    from .service import ArchivoRef, Contexto

PENDIENTE_CARGA = "pendiente_carga"
EN_REVISION = "en_revision"
APROBADO = "aprobado"
RECHAZADO = "rechazado"
FINALIZADO = "finalizado"

DEVUELTO = "devuelto"  # código de la acción de devolver

EXTENSIONES_DOCUMENTO = (".pdf", ".doc", ".docx")

PermisoCallable = Callable[["Contexto", int], Awaitable[bool]]


@dataclass(frozen=True)
class Estado:
    codigo: str
    etiqueta: str
    tono: Tono = "neutral"
    final: bool = False

    def info(self) -> EstadoInfo:
        return EstadoInfo(codigo=self.codigo, etiqueta=self.etiqueta, tono=self.tono)


@dataclass(frozen=True)
class Accion:
    codigo: str
    etiqueta: str  # imperativo, para el botón: "Aprobar"
    _: KW_ONLY
    etiqueta_realizada: str  # participio, para historial/auditoría: "Aprobado"
    tono: Tono = "info"
    # Estado al que lleva. None solo para acciones que ``cuenta_devolucion``
    # (el destino depende del contador) o si la subclase lo resuelve en
    # ``estado_tras_accion``.
    estado_destino: Optional[str] = None
    desde: frozenset[str] = field(default_factory=lambda: frozenset({EN_REVISION}))
    requiere_comentario: bool = False
    adjunto_extensiones: tuple[str, ...] = ()  # vacío = no admite adjunto
    cuenta_devolucion: bool = False
    auditoria: Optional[str] = None  # código de auditoría; default = codigo
    # Ícono semántico para la UI (no el nombre del componente): "aprobar",
    # "devolver", "firmar"... La UI lo traduce; desconocido = sin ícono.
    icono: Optional[str] = None

    @property
    def admite_adjunto(self) -> bool:
        return bool(self.adjunto_extensiones)

    @property
    def codigo_auditoria(self) -> str:
        return self.auditoria or self.codigo


@dataclass(frozen=True)
class EventoAuditoria:
    """Etiqueta y tono con que la UI pinta un código de auditoría."""

    codigo: str
    etiqueta: str
    tono: Tono = "neutral"


ESTADOS_BASE: tuple[Estado, ...] = (
    Estado(PENDIENTE_CARGA, "Pendiente de carga", "neutral"),
    Estado(EN_REVISION, "En revisión", "info"),
    Estado(APROBADO, "Aprobado", "success", final=True),
    Estado(RECHAZADO, "Devuelto", "warning"),
    Estado(FINALIZADO, "Finalizado", "error", final=True),
)

ACCIONES_BASE: tuple[Accion, ...] = (
    Accion(
        APROBADO, "Aprobar", etiqueta_realizada="Aprobado", tono="success",
        estado_destino=APROBADO, auditoria="aprobar", icono="aprobar",
    ),
    Accion(
        DEVUELTO, "Devolver", etiqueta_realizada="Devuelto", tono="warning",
        # El motivo de la devolución es obligatorio (así lo exigía la UI antes
        # del refactor); ahora lo valida el backend y la UI lo lee del contrato.
        requiere_comentario=True,
        adjunto_extensiones=EXTENSIONES_DOCUMENTO,
        cuenta_devolucion=True,
        auditoria="devolver",
        icono="devolver",
    ),
)


# Eventos de auditoría que registra el servicio (además de los de cada acción,
# que se derivan de ``Accion.etiqueta_realizada``/``tono``).
EVENTOS_AUDITORIA_BASE: tuple[EventoAuditoria, ...] = (
    EventoAuditoria("crear", "Proceso creado", "info"),
    EventoAuditoria("subir_version_inicial", "Versión inicial cargada", "info"),
    EventoAuditoria("subir_version", "Nueva versión subida", "info"),
    EventoAuditoria("finalizar", "Finalizado", "error"),
)


class FlujoRevision:
    """Flujo genérico. El paquete no conoce flujos concretos: cada app
    subclasea esto en su propio código."""

    ESTADOS_EXTRA: ClassVar[tuple[Estado, ...]] = ()
    ACCIONES_EXTRA: ClassVar[tuple[Accion, ...]] = ()
    EVENTOS_AUDITORIA_EXTRA: ClassVar[tuple[EventoAuditoria, ...]] = ()

    max_devoluciones: int = 3
    estados_subida: ClassVar[frozenset[str]] = frozenset({RECHAZADO})
    extensiones_version: tuple[str, ...] = EXTENSIONES_DOCUMENTO

    def __init__(
        self,
        *,
        max_devoluciones: int | None = None,
        extensiones_version: tuple[str, ...] | None = None,
        puede_ver: PermisoCallable | None = None,
        puede_revisar: PermisoCallable | None = None,
        puede_subir_version: PermisoCallable | None = None,
    ):
        if max_devoluciones is not None:
            if max_devoluciones < 1:
                raise ValueError("max_devoluciones debe ser >= 1")
            self.max_devoluciones = max_devoluciones
        if extensiones_version is not None:
            self.extensiones_version = tuple(e.lower() for e in extensiones_version)
        self._puede_ver_cb = puede_ver
        self._puede_revisar_cb = puede_revisar
        self._puede_subir_cb = puede_subir_version

        self.estados: dict[str, Estado] = {e.codigo: e for e in (*ESTADOS_BASE, *self.ESTADOS_EXTRA)}
        acciones = {a.codigo: a for a in (*ACCIONES_BASE, *self.ACCIONES_EXTRA)}
        for a in acciones.values():
            if a.estado_destino is None and not a.cuenta_devolucion:
                # La subclase debe resolverlo en estado_tras_accion; se valida en uso.
                continue
            if a.estado_destino is not None and a.estado_destino not in self.estados:
                raise ValueError(f"Acción {a.codigo!r} apunta a estado desconocido {a.estado_destino!r}")
        self.acciones: dict[str, Accion] = acciones
        # Precedencia: base < derivados de acciones < extras de la subclase.
        eventos = {e.codigo: e for e in EVENTOS_AUDITORIA_BASE}
        for a in acciones.values():
            eventos[a.codigo_auditoria] = EventoAuditoria(a.codigo_auditoria, a.etiqueta_realizada, a.tono)
        eventos.update({e.codigo: e for e in self.EVENTOS_AUDITORIA_EXTRA})
        self.eventos_auditoria: dict[str, EventoAuditoria] = eventos

    # ------------------------------------------------------------ catálogo
    def estado_info(self, codigo: str) -> EstadoInfo:
        estado = self.estados.get(codigo)
        if estado is None:
            return EstadoInfo(codigo=codigo, etiqueta=codigo, tono="neutral")
        return estado.info()

    def evento_auditoria(self, codigo: str) -> EventoAuditoria:
        evento = self.eventos_auditoria.get(codigo)
        if evento is None:
            texto = codigo.replace("_", " ").strip()
            return EventoAuditoria(codigo, texto[:1].upper() + texto[1:], "neutral")
        return evento

    def accion_regla(self, accion: Accion, bloqueada: str | None = None) -> AccionRevision:
        return AccionRevision(
            codigo=accion.codigo,
            etiqueta=accion.etiqueta,
            tono=accion.tono,
            requiere_comentario=accion.requiere_comentario,
            adjunto=AdjuntoRegla(permitido=accion.admite_adjunto, extensiones=list(accion.adjunto_extensiones)),
            bloqueada=bloqueada,
            icono=accion.icono,
        )

    # ------------------------------------------------------------ permisos
    async def puede_ver(self, ctx: "Contexto", user_id: int) -> bool:
        if self._puede_ver_cb is not None:
            return await self._puede_ver_cb(ctx, user_id)
        return ctx.proceso.creador_id == user_id or user_id in await ctx.revisores_ids()

    async def puede_revisar(self, ctx: "Contexto", user_id: int) -> bool:
        if self._puede_revisar_cb is not None:
            return await self._puede_revisar_cb(ctx, user_id)
        return user_id in await ctx.revisores_ids()

    async def puede_subir_version(self, ctx: "Contexto", user_id: int) -> bool:
        if self._puede_subir_cb is not None:
            return await self._puede_subir_cb(ctx, user_id)
        return ctx.proceso.creador_id == user_id

    # --------------------------------------------------------- validaciones
    def accion_aplicable(self, proceso: Any, accion: Accion) -> bool:
        """Si la acción se ofrece para este proceso (además de ``desde``)."""
        return True

    async def validar_accion(self, ctx: "Contexto", accion: Accion, user_id: int) -> str | None:
        """Motivo por el que la acción aplica pero no se puede ejecutar ya (o None)."""
        if ctx.proceso.version_actual < 1:
            return "Aún no hay una versión cargada"
        return None

    def subida_permitida_en(self, proceso: Any) -> bool:
        return proceso.estado == PENDIENTE_CARGA or proceso.estado in self.estados_subida

    def extensiones_subida(self, proceso: Any) -> tuple[str, ...]:
        return self.extensiones_version

    async def validar_subida(self, ctx: "Contexto", archivo: "ArchivoRef", user_id: int) -> str | None:
        """Regla extra sobre el archivo a subir (o None). La extensión ya la valida el servicio."""
        return None

    # ---------------------------------------------------------- transiciones
    def estado_tras_accion(self, proceso: Any, accion: Accion) -> str:
        """Estado destino. Se llama DESPUÉS de incrementar numero_devoluciones
        si la acción ``cuenta_devolucion``."""
        if accion.cuenta_devolucion:
            return FINALIZADO if proceso.numero_devoluciones >= self.max_devoluciones else RECHAZADO
        if accion.estado_destino is None:
            raise NotImplementedError(f"La acción {accion.codigo!r} no define estado_destino")
        return accion.estado_destino

    async def despues_de_subida(
        self, ctx: "Contexto", version: Any, user_id: int, estado_anterior: str
    ) -> str:
        """Estado tras subir una versión. Puede registrar revisiones/auditoría
        extra vía ``ctx`` (p. ej. auto-aprobar)."""
        return EN_REVISION

    def auditoria_accion(self, proceso: Any, accion: Accion, estado_nuevo: str) -> tuple[str, str]:
        """(código, descripción) de auditoría para una revisión."""
        if accion.cuenta_devolucion:
            if estado_nuevo == FINALIZADO:
                return "finalizar", f"Finalizado tras {proceso.numero_devoluciones} devoluciones"
            return (
                accion.codigo_auditoria,
                f"Devuelto, devoluciones {proceso.numero_devoluciones}/{self.max_devoluciones}",
            )
        etiqueta = self.estados.get(estado_nuevo).etiqueta if estado_nuevo in self.estados else estado_nuevo
        return accion.codigo_auditoria, f"{accion.etiqueta}: estado {etiqueta}"
