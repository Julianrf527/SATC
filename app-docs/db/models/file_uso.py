"""Dueños de cada archivo (``file_hash``) y registro de quién lo subió.

Con la deduplicación por hash un mismo archivo físico puede pertenecer a varios
módulos y entidades, por eso los dueños van en tabla aparte y no como columnas.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import TIMESTAMP, Column, ForeignKey, Integer, String, UniqueConstraint

from .base import Base


def _ahora() -> datetime:
    return datetime.now(ZoneInfo("America/Bogota"))


class FileUso(Base):
    """Una entidad de un servicio que usa el archivo (``servicio`` lo pone
    app-docs a partir del service-token, nunca el cliente)."""

    __tablename__ = "file_uso"
    __table_args__ = (
        UniqueConstraint("file_id", "servicio", "entidad", "entidad_id", name="uq_file_uso"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("file_hash.id", ondelete="CASCADE"), nullable=False, index=True)
    servicio = Column(String(50), nullable=False)
    entidad = Column(String(50), nullable=False)
    entidad_id = Column(String(64), nullable=False)
    usuario_id = Column(Integer, nullable=True)
    creado_en = Column(TIMESTAMP(timezone=True), default=_ahora, nullable=False)


class FileSubida(Base):
    """Cada subida de un archivo, nueva o deduplicada. Demuestra que el usuario
    tuvo esos bytes: base de la regla que impide asociar archivos ajenos."""

    __tablename__ = "file_subida"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer, ForeignKey("file_hash.id", ondelete="CASCADE"), nullable=False, index=True)
    usuario_id = Column(Integer, nullable=True, index=True)
    servicio_origen = Column(String(50), nullable=False)
    fecha = Column(TIMESTAMP(timezone=True), default=_ahora, nullable=False)
