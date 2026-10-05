"""Mixins SQLAlchemy del proceso de revisión.

Cada app los combina con SU ``Base`` y SUS nombres de tabla::

    class InformeProceso(ProcesoRevisionMixin, Base):
        __tablename__ = "informe_procesos"

    class InformeVersion(VersionRevisionMixin, Base):
        __tablename__ = "informe_versiones"
        __proceso_tabla__ = "informe_procesos"

Las tablas hijas resuelven la FK por ``__proceso_tabla__`` (obligatorio). El
nombre de la columna FK es ``proceso_id`` salvo que se defina
``__proceso_fk_columna__`` (p. ej. ``"documento_id"`` para reusar tablas
existentes). Cualquier otra columna se puede renombrar redefiniendo el
atributo en la clase concreta (``creador_id = mapped_column("usuario_creador_id", Integer, index=True)``):
el servicio solo usa los nombres de atributo Python.

No se usa ``@declarative_mixin``: en SQLAlchemy 2.1 está deprecado (solo
servía al plugin de mypy); los mixins funcionan igual sin él.

Los archivos se referencian por ``file_id`` (id de ``file_hash`` en app-docs)
además de url/nombre/size, para poder llevar ``numero_usos``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, ClassVar

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

try:  # pragma: no cover - depende de la plataforma
    from zoneinfo import ZoneInfo

    ZONA_SATC = ZoneInfo("America/Bogota")
except Exception:  # pragma: no cover - Windows sin tzdata
    ZONA_SATC = timezone.utc


def ahora() -> datetime:
    return datetime.now(ZONA_SATC)


class ProcesoRevisionMixin:
    """Cabecera del proceso. ``version_actual == 0`` significa sin versiones."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(255))
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(30), index=True)
    creador_id: Mapped[int] = mapped_column(Integer, index=True)
    version_actual: Mapped[int] = mapped_column(Integer, default=0)
    numero_devoluciones: Mapped[int] = mapped_column(Integer, default=0)
    fecha_creacion: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=ahora, index=True)
    fecha_ultima_actualizacion: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), default=ahora, onupdate=ahora
    )


class _HijoDeProceso:
    __proceso_tabla__: ClassVar[str]
    __proceso_fk_columna__: ClassVar[str] = "proceso_id"

    @declared_attr
    def proceso_id(cls) -> Mapped[int]:
        tabla = getattr(cls, "__proceso_tabla__", None)
        if not tabla:
            raise TypeError(f"{cls.__name__} debe definir __proceso_tabla__ (tabla del proceso)")
        return mapped_column(
            cls.__proceso_fk_columna__,
            Integer,
            ForeignKey(f"{tabla}.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        )


class AsignacionRevisorMixin(_HijoDeProceso):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    revisor_id: Mapped[int] = mapped_column(Integer, index=True)
    fecha_asignacion: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=ahora)
    notificado: Mapped[bool] = mapped_column(Boolean, default=False)


class VersionRevisionMixin(_HijoDeProceso):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_version: Mapped[int] = mapped_column(Integer)
    file_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    archivo_url: Mapped[str] = mapped_column(String(500))
    archivo_nombre: Mapped[str] = mapped_column(String(255))
    archivo_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    usuario_subida_id: Mapped[int] = mapped_column(Integer)
    comentario: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_subida: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=ahora)


class RevisionMixin(_HijoDeProceso):
    """Una acción de un revisor sobre una versión. ``accion`` guarda el código
    de la acción ejecutada (``aprobado``, ``devuelto``, extras...)."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_revisada: Mapped[int] = mapped_column(Integer)
    revisor_id: Mapped[int] = mapped_column(Integer, index=True)
    accion: Mapped[str] = mapped_column(String(30))
    comentarios: Mapped[str | None] = mapped_column(Text, nullable=True)
    adjunto_file_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    adjunto_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    adjunto_nombre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    adjunto_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    fecha_revision: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=ahora)


class AuditoriaRevisionMixin(_HijoDeProceso):
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    accion: Mapped[str] = mapped_column(String(50))
    usuario_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    datos_adicionales: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    fecha_accion: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=ahora)
