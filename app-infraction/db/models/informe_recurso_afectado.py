from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import TIMESTAMP, Boolean, Column, Integer, String, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base

RECURSOS_MATRIZ = [
    "AIRE", "SUELO", "AGUA", "PAISAJE", "FLORA", "FAUNA", "RUIDO", "SOCIAL", "OTRO",
]


class InformeRecursoAfectado(Base):
    """
    Matriz de recursos afectados (magnitud/reversibilidad) diligenciada por el
    profesional asignado, solo para informes de VISITA ya aceptados. Una fila
    fija por cada recurso de RECURSOS_MATRIZ.
    """
    __tablename__ = 'informe_recurso_afectado'

    id = Column(Integer, primary_key=True, autoincrement=True)
    informe_id = Column(
        Integer,
        ForeignKey('informe_tecnico.id', onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    recurso = Column(String(20), nullable=False)
    magnitud = Column(String(20))  # LEVE | MODERADO | GRAVE
    reversibilidad = Column(String(20))  # REVERSIBLE | IRREVERSIBLE
    no_existe = Column(Boolean, nullable=False, default=False)
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    informe = relationship("InformeTecnico")

    __table_args__ = (
        UniqueConstraint('informe_id', 'recurso', name='uq_informe_recurso'),
        Index('ix_informe_recurso_afectado_informe', 'informe_id'),
    )
