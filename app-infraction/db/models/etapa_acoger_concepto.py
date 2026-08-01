from sqlalchemy import Column, Integer, ForeignKey, Date, TIMESTAMP, Index, String
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class EtapaAcogerConcepto(Base):
    __tablename__ = 'etapa_acoger_concepto'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_acogida_concepto = Column(String(30), nullable=False)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    dias_termino = Column(Integer)
    fecha_termino_calculada = Column(Date)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"))
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    expediente = relationship("Expediente", back_populates="etapa_acoger_concepto")
    acto_administrativo = relationship("ActoAdministrativo", back_populates="etapa_acoger_concepto")
    oficio_remite = relationship("OficioRemite", back_populates="etapa_acoger_concepto", uselist=False, cascade="all, delete-orphan")
    solicitud_informacion = relationship("SolicitudInformacion", back_populates="etapa_acoger_concepto", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_etapa_acoger_concepto_expediente', 'expediente_id'),
    )
