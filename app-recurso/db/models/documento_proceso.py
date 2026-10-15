"""Proceso de revisión de los documentos que se proyectan en esta app (plan §5).

Replica el modelo de infraction-app (``informe_proceso``) con los mixins de
``satc_shared.review_process``. app-docs solo almacena los archivos.

Un proceso documenta UNA fila de etapa: ``(etapa_tipo, etapa_ref_id)`` es la
tabla y el id de esa fila (``acto_admite``, ``requerimiento``, ``decision``,
``recurso_reposicion``, ``memorias_calculo``, ``recibo_satisfaccion_obras``,
``expediente_involucrado`` para el acto que reconoce al tercero, o
``concepto_tecnico``). Referencia polimórfica: sin FK real a la etapa, pero
``expediente_id`` sí tiene FK para borrar en cascada y listar por expediente.

``tipo_documento`` decide la cadena de revisores (ver
``services/revision_documentos.py``) y ``paso_actual`` el paso de esa cadena
en el que está la revisión. ``activo`` marca el proceso vigente de la etapa
(a lo sumo uno, índice único parcial).
"""
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, text
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

TABLA_PROCESO = "documento_proceso"


class DocumentoProceso(ProcesoRevisionMixin, Base):
    __tablename__ = TABLA_PROCESO

    expediente_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("expediente.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tipo_documento: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    etapa_tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    etapa_ref_id: Mapped[int] = mapped_column(Integer, nullable=False)
    paso_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

    expediente = relationship("Expediente")

    __table_args__ = (
        Index("ix_documento_proceso_etapa", "etapa_tipo", "etapa_ref_id"),
        Index(
            "uq_documento_proceso_activo",
            "etapa_tipo",
            "etapa_ref_id",
            unique=True,
            postgresql_where=text("activo"),
        ),
    )


class DocumentoProcesoVersion(VersionRevisionMixin, Base):
    __tablename__ = "documento_proceso_version"
    __proceso_tabla__ = TABLA_PROCESO


class DocumentoProcesoRevision(RevisionMixin, Base):
    __tablename__ = "documento_proceso_revision"
    __proceso_tabla__ = TABLA_PROCESO

    # Paso de la cadena y permiso de revisor con que se hizo la revisión: un
    # permiso que ya aprobó o devolvió en un paso no vuelve a revisar (plan §5.2).
    paso: Mapped[int | None] = mapped_column(Integer, nullable=True)
    permiso: Mapped[str | None] = mapped_column(String(50), nullable=True)


class DocumentoProcesoAuditoria(AuditoriaRevisionMixin, Base):
    __tablename__ = "documento_proceso_auditoria"
    __proceso_tabla__ = TABLA_PROCESO


class DocumentoProcesoRevisor(AsignacionRevisorMixin, Base):
    __tablename__ = "documento_proceso_revisor"
    __proceso_tabla__ = TABLA_PROCESO


MODELOS_DOCUMENTO = ReviewModels(
    proceso=DocumentoProceso,
    version=DocumentoProcesoVersion,
    revision=DocumentoProcesoRevision,
    auditoria=DocumentoProcesoAuditoria,
    asignacion=DocumentoProcesoRevisor,
)
