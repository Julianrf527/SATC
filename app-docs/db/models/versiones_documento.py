"""Versiones de un documento (tabla existente ``versiones_documento``).

    proceso_id      -> documento_id   (vía __proceso_fk_columna__)
    archivo_nombre  -> archivo_nombre_original
    file_id         -> columna nueva (id en file_hash), agregada por db/migrations.py
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from satc_shared.review_process import VersionRevisionMixin

from .base import Base


class VersionDocumento(VersionRevisionMixin, Base):
    __tablename__ = "versiones_documento"
    __proceso_tabla__ = "documentos"
    __proceso_fk_columna__ = "documento_id"

    archivo_nombre: Mapped[str] = mapped_column("archivo_nombre_original", String(255))
