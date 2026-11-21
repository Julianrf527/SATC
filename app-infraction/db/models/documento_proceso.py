"""Proceso de revisión de los documentos de infracciones: informes técnicos y
actos administrativos. Una sola familia de tablas, como ``documento_proceso``
de app-recurso, con los mixins de ``satc_shared.review_process``.

Un proceso documenta UNA fila de etapa: ``(etapa_tipo, etapa_ref_id)``

- ``informe_tecnico``     → ``informe_tecnico.id`` (VISITA o SEGUIMIENTO)
- ``medida_preventiva``   → ``medida_preventiva.id`` (su acto)
- ``etapa_concepto``      → ``etapa_acoger_concepto.id`` (su acto; las dos
  instancias, visita y seguimiento: ``tipo_documento`` las distingue)
- ``etapa_cierre``        → ``etapa_cierre.id`` (su acto)

Referencia polimórfica: sin FK real a la etapa (quien borra la etapa borra sus
procesos, ver services/cascada_etapas.py); ``expediente_id`` sí tiene FK para
borrar en cascada y listar por expediente. ``tipo_documento`` decide el flujo
(quién sube, quién revisa, tope de devoluciones). ``activo`` marca el proceso
vigente de la etapa (a lo sumo uno, índice único parcial). ``asignador_id``
solo lo usan los informes (quien asignó técnico y líder técnico).
"""
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

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

# etapa_tipo
ETAPA_INFORME = "informe_tecnico"
ETAPA_MEDIDA = "medida_preventiva"
ETAPA_CONCEPTO = "etapa_concepto"
ETAPA_CIERRE = "etapa_cierre"
ETAPAS_ACTO = (ETAPA_MEDIDA, ETAPA_CONCEPTO, ETAPA_CIERRE)

# tipo_documento
INFORME_VISITA = "INFORME_VISITA"
INFORME_SEGUIMIENTO = "INFORME_SEGUIMIENTO"
ACTO_MEDIDA = "ACTO_MEDIDA"
ACTO_CONCEPTO = "ACTO_CONCEPTO"
ACTO_CONCEPTO_SEGUIMIENTO = "ACTO_CONCEPTO_SEGUIMIENTO"
ACTO_CIERRE = "ACTO_CIERRE"

TIPO_ACTO_POR_ETAPA = {ETAPA_MEDIDA: ACTO_MEDIDA, ETAPA_CONCEPTO: ACTO_CONCEPTO, ETAPA_CIERRE: ACTO_CIERRE}


def tipo_documento_informe(tipo_informe: Optional[str]) -> str:
    return INFORME_SEGUIMIENTO if (tipo_informe or "").upper() == "SEGUIMIENTO" else INFORME_VISITA


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
    # Informes: quien asignó (ASSIGN_REPORTS); ve el proceso y recibe el aviso de reasignar.
    asignador_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))

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

    @property
    def es_informe(self) -> bool:
        return self.etapa_tipo == ETAPA_INFORME

    @property
    def es_acto(self) -> bool:
        return self.etapa_tipo in ETAPAS_ACTO

    @property
    def informe_id(self) -> Optional[int]:
        """Id del informe técnico (solo procesos de informe)."""
        return self.etapa_ref_id if self.es_informe else None


class DocumentoProcesoVersion(VersionRevisionMixin, Base):
    __tablename__ = "documento_proceso_version"
    __proceso_tabla__ = TABLA_PROCESO


class DocumentoProcesoRevision(RevisionMixin, Base):
    __tablename__ = "documento_proceso_revision"
    __proceso_tabla__ = TABLA_PROCESO


class DocumentoProcesoAuditoria(AuditoriaRevisionMixin, Base):
    __tablename__ = "documento_proceso_auditoria"
    __proceso_tabla__ = TABLA_PROCESO


class DocumentoProcesoRevisor(AsignacionRevisorMixin, Base):
    """Revisores ASIGNADOS (líder técnico del informe). Los actos se revisan
    por permiso (``infraccion_lider_proyecto``) y no usan esta tabla."""

    __tablename__ = "documento_proceso_revisor"
    __proceso_tabla__ = TABLA_PROCESO


MODELOS_DOCUMENTO = ReviewModels(
    proceso=DocumentoProceso,
    version=DocumentoProcesoVersion,
    revision=DocumentoProcesoRevision,
    auditoria=DocumentoProcesoAuditoria,
    asignacion=DocumentoProcesoRevisor,
)
