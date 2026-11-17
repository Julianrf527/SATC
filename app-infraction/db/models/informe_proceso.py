"""Proceso de revisión PROPIO del informe técnico (antes vivía en app-docs como
documento con origen='informe_tecnico' + tabla puente informe_documento).

Combina los mixins de ``satc_shared.review_process`` con el Base de
infracciones. Un informe técnico puede tener varios procesos (uno por
asignación); ``activo`` marca el vigente (índice único parcial: a lo sumo uno
activo por informe). Al reasignar o cambiar a modo MANUAL el vigente se
finaliza y queda ``activo=False``.
"""
from sqlalchemy import Boolean, ForeignKey, Index, Integer, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from satc_shared.review_process import (
    AsignacionRevisorMixin,
    AuditoriaRevisionMixin,
    ProcesoRevisionMixin,
    ReviewModels,
    RevisionMixin,
    VersionRevisionMixin,
)

from .base import Base

TABLA_PROCESO = "informe_proceso"


class InformeProceso(ProcesoRevisionMixin, Base):
    __tablename__ = TABLA_PROCESO

    informe_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("informe_tecnico.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Quien asignó (ASSIGN_REPORTS): ve el proceso y recibe el aviso de reasignar.
    asignador_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    informe = relationship("InformeTecnico", back_populates="procesos_revision")

    __table_args__ = (
        Index(
            "uq_informe_proceso_activo",
            "informe_id",
            unique=True,
            postgresql_where=text("activo"),
        ),
    )


class InformeProcesoVersion(VersionRevisionMixin, Base):
    __tablename__ = "informe_proceso_version"
    __proceso_tabla__ = TABLA_PROCESO


class InformeProcesoRevision(RevisionMixin, Base):
    __tablename__ = "informe_proceso_revision"
    __proceso_tabla__ = TABLA_PROCESO


class InformeProcesoAuditoria(AuditoriaRevisionMixin, Base):
    __tablename__ = "informe_proceso_auditoria"
    __proceso_tabla__ = TABLA_PROCESO


class InformeProcesoRevisor(AsignacionRevisorMixin, Base):
    __tablename__ = "informe_proceso_revisor"
    __proceso_tabla__ = TABLA_PROCESO


MODELOS_INFORME = ReviewModels(
    proceso=InformeProceso,
    version=InformeProcesoVersion,
    revision=InformeProcesoRevision,
    auditoria=InformeProcesoAuditoria,
    asignacion=InformeProcesoRevisor,
)
