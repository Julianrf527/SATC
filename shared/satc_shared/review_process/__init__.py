"""Helper genérico de proceso de revisión de documentos (sin estadísticas).

El paquete NO conoce flujos concretos: cada app combina los mixins con su
``Base`` y sus tablas, y subclasea ``FlujoRevision`` para sus reglas.
Ver shared/README.md.
"""
from .errors import (
    ErrorUsoArchivo,
    PermisoDenegado,
    ProcesoNoEncontrado,
    ReviewError,
    TransicionInvalida,
    ValidacionError,
    VersionDuplicada,
)
from .flow import (
    ACCIONES_BASE,
    APROBADO,
    DEVUELTO,
    EN_REVISION,
    ESTADOS_BASE,
    EVENTOS_AUDITORIA_BASE,
    EXTENSIONES_DOCUMENTO,
    FINALIZADO,
    PENDIENTE_CARGA,
    RECHAZADO,
    Accion,
    Estado,
    EventoAuditoria,
    FlujoRevision,
)
from .models import (
    AsignacionRevisorMixin,
    AuditoriaRevisionMixin,
    ProcesoRevisionMixin,
    RevisionMixin,
    VersionRevisionMixin,
)
from .schemas import (
    AccionRevision,
    AdjuntoRegla,
    ArchivoInfo,
    AuditoriaInfo,
    EstadoInfo,
    ProcesoDetalle,
    RevisionInfo,
    RevisorInfo,
    SubidaVersion,
    Tono,
    VersionInfo,
)
from .service import (
    ArchivoRef,
    Contexto,
    FileUsageTracker,
    ProcesoRevisionService,
    ResultadoRevision,
    ResultadoVersion,
    ReviewModels,
)

__all__ = [
    "ACCIONES_BASE", "APROBADO", "DEVUELTO", "EN_REVISION", "ESTADOS_BASE", "EVENTOS_AUDITORIA_BASE",
    "EXTENSIONES_DOCUMENTO", "FINALIZADO", "PENDIENTE_CARGA", "RECHAZADO",
    "Accion", "AccionRevision", "AdjuntoRegla", "ArchivoInfo", "ArchivoRef",
    "AsignacionRevisorMixin", "AuditoriaInfo", "AuditoriaRevisionMixin", "Contexto",
    "ErrorUsoArchivo", "Estado", "EstadoInfo", "EventoAuditoria", "FileUsageTracker", "FlujoRevision",
    "PermisoDenegado", "ProcesoDetalle", "ProcesoNoEncontrado", "ProcesoRevisionMixin",
    "ProcesoRevisionService", "ResultadoRevision", "ResultadoVersion", "ReviewError",
    "ReviewModels", "RevisionInfo", "RevisionMixin", "RevisorInfo", "SubidaVersion",
    "TransicionInvalida", "ValidacionError", "VersionDuplicada", "VersionInfo",
    "VersionRevisionMixin",
]
