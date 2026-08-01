from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Expediente(Base):
    __tablename__ = 'expediente'

    id = Column(Integer, primary_key=True, autoincrement=True)
    radicado = Column(String(15), unique=True)
    expediente = Column(String(7), unique=True)
    motivo_afectacion = Column(String(200))
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    encargado_id = Column(Integer, index=True)
    direccion = Column(String(100))
    vereda_id = Column(Integer, ForeignKey('vereda.id', onupdate="CASCADE"), index=True)
    archivado = Column(Boolean, default=False, index=True)
    fecha_archivado = Column(TIMESTAMP(timezone=True), nullable=True)

    vereda = relationship("Vereda", back_populates="expedientes")
    involucrados = relationship("ExpedienteInvolucrado", back_populates="expediente", cascade="all, delete-orphan")
    recursos = relationship("ExpedienteRecurso", back_populates="expediente", cascade="all, delete-orphan")

    # Una etapa por tipo (UNIQUE en expediente_id garantiza max 1)
    etapa_indagacion = relationship("EtapaIndagacion", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    etapa_medida_preventiva = relationship("EtapaMedidaPreventiva", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    etapa_inicio_sancionatorio = relationship("EtapaInicioSancionatorio", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    etapa_cesacion = relationship("EtapaCesacion", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    etapa_formulacion_cargos = relationship("EtapaFormulacionCargos", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    etapa_apertura_probatoria = relationship("EtapaAperturaProbatoria", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    etapa_cierre_probatoria = relationship("EtapaCierreProbatoria", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    etapa_decision_fondo = relationship("EtapaDecisionFondo", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    etapa_probatoria_recurso = relationship("EtapaProbatoriaRecurso", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    etapa_ejecucion_sancion = relationship("EtapaEjecucionSancion", back_populates="expediente", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        # Listar "mis expedientes" ordenados por fecha — filtro + orden más frecuente
        Index("ix_expediente_encargado_fecha", "encargado_id", "fecha_creacion"),
    )
