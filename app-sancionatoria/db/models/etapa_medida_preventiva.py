from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class EtapaMedidaPreventiva(Base):
    __tablename__ = 'etapa_medida_preventiva'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', ondelete='CASCADE'), unique=True, nullable=False)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', ondelete='SET NULL'), nullable=True, index=True)
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    tipo_medida_id = Column(Integer, ForeignKey('tipo_medida.id'), nullable=True)
    cantidad = Column(Text, nullable=True)
    especie = Column(Text, nullable=True)
    estado_medida = Column(Boolean, nullable=True)

    expediente = relationship("Expediente", back_populates="etapa_medida_preventiva")
    acto_administrativo = relationship("ActoAdministrativo", foreign_keys=[acto_administrativo_id])
    tipo_medida = relationship("TipoMedida")
