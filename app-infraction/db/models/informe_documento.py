from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base


class InformeDocumento(Base):
    """
    Tabla puente entre InformeTecnico y el proceso de revisión en app-docs.
    Cada informe puede tener múltiples procesos (uno activo a la vez).
    Cuando se reasigna el profesional, el proceso activo se finaliza y se crea uno nuevo.
    """
    __tablename__ = 'informe_documento'

    id = Column(Integer, primary_key=True, autoincrement=True)
    informe_id = Column(
        Integer,
        ForeignKey('informe_tecnico.id', onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False
    )
    docs_documento_id = Column(Integer, nullable=False)  # ID de Documento en app-docs
    activo = Column(Boolean, default=True, nullable=False)  # Solo uno activo por informe
    fecha_creacion = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )

    informe = relationship("InformeTecnico", back_populates="documentos_proceso")

    __table_args__ = (
        Index('ix_informe_documento_informe', 'informe_id'),
        Index('ix_informe_documento_docs_id', 'docs_documento_id'),
    )
