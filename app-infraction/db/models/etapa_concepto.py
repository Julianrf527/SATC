from sqlalchemy import Column, Integer, ForeignKey, Date, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class EtapaConcepto(Base):
    __tablename__ = 'etapa_concepto'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    fecha_auto_indagacion = Column(Date)
    termino = Column(Integer)
    fecha_termino_calculada = Column(Date)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"))
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    expediente = relationship("Expediente", back_populates="etapa_concepto")
    acto_administrativo = relationship("ActoAdministrativo", back_populates="etapa_concepto")

    __table_args__ = (
        Index('ix_etapa_concepto_expediente', 'expediente_id')
    )
