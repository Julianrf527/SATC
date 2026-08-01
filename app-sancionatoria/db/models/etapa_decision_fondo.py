from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class EtapaDecisionFondo(Base):
    __tablename__ = 'etapa_decision_fondo'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', ondelete='CASCADE'), unique=True, nullable=False)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', ondelete='SET NULL'), nullable=True, index=True)
    # Acto de recurso (cuando el investigado interpone recurso desde esta etapa)
    acto_recurso_id = Column(Integer, ForeignKey('acto_administrativo.id', ondelete='SET NULL'), nullable=True, index=True)
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    tipo_sancion_id = Column(Integer, ForeignKey('tipo_sancion.id'), nullable=True)
    detalle = Column(Text, nullable=True)

    expediente = relationship("Expediente", back_populates="etapa_decision_fondo")
    acto_administrativo = relationship("ActoAdministrativo", foreign_keys=[acto_administrativo_id])
    acto_recurso = relationship("ActoAdministrativo", foreign_keys=[acto_recurso_id])
    tipo_sancion = relationship("TipoSancion")
    anexos = relationship("DocumentoAnexo", primaryjoin="and_(DocumentoAnexo.etapa_tipo=='decision_fondo', foreign(DocumentoAnexo.etapa_ref_id)==EtapaDecisionFondo.id)", viewonly=True)
