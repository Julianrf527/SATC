"""Revisores asignados a un documento (tabla existente ``asignaciones_revisores``).

    proceso_id -> documento_id
"""
from satc_shared.review_process import AsignacionRevisorMixin

from .base import Base


class AsignacionRevisor(AsignacionRevisorMixin, Base):
    __tablename__ = "asignaciones_revisores"
    __proceso_tabla__ = "documentos"
    __proceso_fk_columna__ = "documento_id"
