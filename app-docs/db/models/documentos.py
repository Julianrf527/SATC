"""Proceso de revisión del módulo Documentos (tabla existente ``documentos``).

Columnas del mixin ``ProcesoRevisionMixin`` mapeadas a los nombres reales de la
tabla en producción (no se renombra nada en BD):
    creador_id  -> usuario_creador_id
"""
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from satc_shared.review_process import ProcesoRevisionMixin

from .base import Base


class Documento(ProcesoRevisionMixin, Base):
    __tablename__ = "documentos"

    # Ancho real de la columna en producción (el mixin usa 30).
    estado: Mapped[str] = mapped_column(String(20), index=True)
    creador_id: Mapped[int] = mapped_column("usuario_creador_id", Integer, index=True)
    # Propio de app-docs: tipo declarado al crear (pdf/doc/docx).
    tipo_archivo: Mapped[str | None] = mapped_column(String(10), nullable=True)
