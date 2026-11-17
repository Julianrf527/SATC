"""Revisiones de un documento (tabla existente ``revisiones``).

    proceso_id      -> documento_id
    accion          -> estado_revision   ('aprobado' | 'devuelto')
    adjunto_url     -> archivo_adjunto_url
    adjunto_nombre  -> archivo_adjunto_nombre
    adjunto_file_id, adjunto_size -> columnas nuevas (db/migrations.py)
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from satc_shared.review_process import RevisionMixin

from .base import Base


class Revision(RevisionMixin, Base):
    __tablename__ = "revisiones"
    __proceso_tabla__ = "documentos"
    __proceso_fk_columna__ = "documento_id"

    accion: Mapped[str] = mapped_column("estado_revision", String(20))
    adjunto_url: Mapped[str | None] = mapped_column("archivo_adjunto_url", String(500), nullable=True)
    adjunto_nombre: Mapped[str | None] = mapped_column("archivo_adjunto_nombre", String(255), nullable=True)
