from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class EtapaFormulacionCargos(Base):
    __tablename__ = 'etapa_formulacion_cargos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', ondelete='CASCADE'), unique=True, nullable=False)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', ondelete='SET NULL'), nullable=True, index=True)
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    descargos = Column(Boolean, nullable=True)
    documento_id = Column(Integer, nullable=True)  # ref → app-docs

    expediente = relationship("Expediente", back_populates="etapa_formulacion_cargos")
    acto_administrativo = relationship("ActoAdministrativo", foreign_keys=[acto_administrativo_id])
