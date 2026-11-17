"""Contrato Pydantic de respuesta del proceso de revisión (lo consume el frontend).

``ProcesoDetalle.acciones_disponibles`` se calcula POR USUARIO y es la fuente
de verdad para la UI: el frontend no debe deducir botones a partir del estado.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

Tono = Literal["info", "success", "warning", "error", "neutral"]


class EstadoInfo(BaseModel):
    codigo: str
    etiqueta: str
    tono: Tono


class AdjuntoRegla(BaseModel):
    permitido: bool
    extensiones: list[str]


class AccionRevision(BaseModel):
    codigo: str
    etiqueta: str  # imperativo, para el botón ("Aprobar")
    tono: Tono
    requiere_comentario: bool
    adjunto: AdjuntoRegla  # siempre presente; ``permitido=False`` si no admite adjunto
    bloqueada: str | None = None  # motivo si la acción aplica pero no se puede ejecutar ya
    icono: str | None = None  # ícono semántico ("aprobar", "devolver", "firmar"...)


class SubidaVersion(BaseModel):
    permitida: bool
    extensiones: list[str]
    motivo: str | None = None  # por qué no está permitida (si aplica)


class ArchivoInfo(BaseModel):
    file_id: int | None = None
    url: str | None = None
    nombre: str | None = None
    size: int | None = None


class RevisorInfo(BaseModel):
    revisor_id: int
    nombre: str | None = None
    fecha_asignacion: datetime | None = None
    notificado: bool = False


class VersionInfo(BaseModel):
    version_id: int
    numero_version: int
    archivo: ArchivoInfo
    usuario_subida_id: int | None = None
    comentario: str = ""
    fecha_subida: datetime | None = None


class RevisionInfo(BaseModel):
    revision_id: int
    revisor_id: int
    revisor_nombre: str
    accion: str
    accion_etiqueta: str  # participio ("Aprobado", "Devuelto", "Aprobado para firma")
    tono: Tono
    comentarios: str = ""
    version_revisada: int | None = None
    fecha_revision: datetime | None = None
    adjunto: ArchivoInfo | None = None


class AuditoriaInfo(BaseModel):
    auditoria_id: int
    usuario_id: int | None = None
    accion: str
    accion_etiqueta: str  # la define el flujo (``FlujoRevision.evento_auditoria``)
    tono: Tono
    descripcion: str = ""
    datos_adicionales: dict[str, Any] | None = None
    fecha_accion: datetime | None = None


class ProcesoDetalle(BaseModel):
    id: int
    nombre: str
    descripcion: str
    estado: EstadoInfo
    version_actual: int
    numero_devoluciones: int
    max_devoluciones: int
    creador_id: int
    fecha_creacion: datetime | None = None
    fecha_ultima_actualizacion: datetime | None = None
    revisores: list[RevisorInfo]
    versiones: list[VersionInfo]      # más reciente primero
    revisiones: list[RevisionInfo]    # más reciente primero
    auditoria: list[AuditoriaInfo]    # cronológica
    acciones_disponibles: list[AccionRevision]
    subida_version: SubidaVersion | None  # None: el usuario no puede subir versiones en este proceso
