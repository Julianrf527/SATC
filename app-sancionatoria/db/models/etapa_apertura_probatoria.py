from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class EtapaAperturaProbatoria(Base):
    __tablename__ = 'etapa_apertura_probatoria'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', ondelete='CASCADE'), unique=True, nullable=False)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', ondelete='SET NULL'), nullable=True, index=True)
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    expediente = relationship("Expediente", back_populates="etapa_apertura_probatoria")
    acto_administrativo = relationship("ActoAdministrativo", foreign_keys=[acto_administrativo_id])
    anexos = relationship("DocumentoAnexo", primaryjoin="and_(DocumentoAnexo.etapa_tipo=='apertura_probatoria', foreign(DocumentoAnexo.etapa_ref_id)==EtapaAperturaProbatoria.id)", viewonly=True)
