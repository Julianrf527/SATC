from sqlalchemy import Column, Integer, ForeignKey, Date, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class EtapaCierre(Base):
    __tablename__ = 'etapa_cierre'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"))
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    
    expediente = relationship("Expediente", back_populates="etapa_cierre")
    acto_administrativo = relationship("ActoAdministrativo", back_populates="etapa_cierre")

    __table_args__ = (
        Index('ix_etapa_cierre_expediente', 'expediente_id'),
    )
