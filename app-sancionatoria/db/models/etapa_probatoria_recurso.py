from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class EtapaProbatoriaRecurso(Base):
    __tablename__ = 'etapa_probatoria_recurso'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', ondelete='CASCADE'), unique=True, nullable=False)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', ondelete='SET NULL'), nullable=True, index=True)
    # Acto de decisión del recurso (acto auxiliar, nivel_auxiliar=true). Columna
    # agregada en producción por db/migrations.py (create_all no altera tablas).
    acto_decision_id = Column(Integer, ForeignKey('acto_administrativo.id', ondelete='SET NULL'), nullable=True, index=True)
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    expediente = relationship("Expediente", back_populates="etapa_probatoria_recurso")
    acto_administrativo = relationship("ActoAdministrativo", foreign_keys=[acto_administrativo_id])
    acto_decision = relationship("ActoAdministrativo", foreign_keys=[acto_decision_id])
