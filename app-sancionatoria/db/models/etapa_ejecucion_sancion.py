from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, String, Boolean, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class EtapaEjecucionSancion(Base):
    __tablename__ = 'etapa_ejecucion_sancion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', ondelete='CASCADE'), unique=True, nullable=False)
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    tipo_acto = Column(String(15), nullable=True)
    fecha_auto = Column(Date, nullable=True)
    documento_acto_administrativo_id = Column(Integer, nullable=True)  # ref → app-docs
    cobro_coactivo = Column(Boolean, nullable=True)
    documento_cobro_id = Column(Integer, nullable=True)
    disposicion = Column(Boolean, nullable=True)
    ruia = Column(Boolean, nullable=True)
    documento_ruia_id = Column(Integer, nullable=True)
    memorando = Column(Boolean, nullable=True)
    documento_memorando_id = Column(Integer, nullable=True)

    expediente = relationship("Expediente", back_populates="etapa_ejecucion_sancion")
