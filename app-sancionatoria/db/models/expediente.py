from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Expediente(Base):
    __tablename__ = 'expediente'

    id = Column(Integer, primary_key=True, autoincrement=True)
    radicado = Column(String(10), unique=True)
    expediente = Column(String(7), unique=True)
    motivo_afectacion = Column(String(200))
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    encargado_id = Column(Integer)
    direccion = Column(String(100))
    vereda_id = Column(Integer, ForeignKey('vereda.id', onupdate="CASCADE"))
    archivado = Column(Boolean, default=False)
    fecha_archivado = Column(TIMESTAMP(timezone=True), nullable=True)

    vereda = relationship("Vereda", back_populates="expedientes")
    etapas = relationship("Etapa", back_populates="expediente", cascade="all, delete-orphan")
    involucrados = relationship("ExpedienteInvolucrado", back_populates="expediente", cascade="all, delete-orphan")
    recursos = relationship("ExpedienteRecurso", back_populates="expediente", cascade="all, delete-orphan")
