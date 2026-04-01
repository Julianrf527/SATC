from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Etapa(Base):
    __tablename__ = 'etapa'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', ondelete="CASCADE", onupdate="CASCADE"))
    tipo_etapa_id = Column(Integer, ForeignKey('tipo_etapa.id'))
    fecha_inicio = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    expediente = relationship("Expediente", back_populates="etapas")
    tipo_etapa = relationship("TipoEtapa", back_populates="etapas")

    actos_administrativos = relationship("ActoAdministrativo", back_populates="etapa", cascade="all, delete-orphan")
    anexos = relationship("Anexo", back_populates="etapa", cascade="all, delete-orphan")
    formulacion_cargos = relationship("FormulacionCargos", back_populates="etapa", uselist=False, cascade="all, delete-orphan")
    decision_fondo = relationship("DecisionFondo", back_populates="etapa", uselist=False, cascade="all, delete-orphan")
    cesacion = relationship("Cesacion", back_populates="etapa", uselist=False, cascade="all, delete-orphan")
    ejecucion_sancion = relationship("EjecucionSancion", back_populates="etapa", uselist=False, cascade="all, delete-orphan")
    medida_preventiva = relationship("MedidaPreventiva", back_populates="etapa", uselist=False, cascade="all, delete-orphan")
