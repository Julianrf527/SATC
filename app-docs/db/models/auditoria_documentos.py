"""Auditoría de un documento (tabla existente ``auditoria_documentos``).

    proceso_id -> documento_id
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from satc_shared.review_process import AuditoriaRevisionMixin

from .base import Base


class AuditoriaDocumento(AuditoriaRevisionMixin, Base):
    __tablename__ = "auditoria_documentos"
    __proceso_tabla__ = "documentos"
    __proceso_fk_columna__ = "documento_id"

    # Columna histórica propia de app-docs (no la usa el servicio genérico).
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
