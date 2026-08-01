from sqlalchemy import Column, Integer, BigInteger, String, Boolean, ForeignKey, Date, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Expediente(Base):
    __tablename__ = 'expediente'

    id = Column(Integer, primary_key=True, autoincrement=True)
    radicado = Column(String(15), unique=True)
    fecha_radicado = Column(Date)
    vereda_id = Column(Integer, ForeignKey('vereda.id', onupdate="CASCADE", ondelete="RESTRICT"))
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    abogado_responsable_id = Column(Integer)
    direccion = Column(String(100))
    descripcion = Column(String(400))
    archivado = Column(Boolean, default=False)

    vereda = relationship("Vereda", back_populates="expedientes")
    tipos_afectacion = relationship("TipoAfectacion", secondary="expediente_tipo_afectacion")
    quejosos = relationship("Quejoso", secondary="quejoso_expediente", back_populates="expedientes")
    involucrados = relationship("ExpedienteInvolucrado", back_populates="expediente", cascade="all, delete-orphan")
    recursos = relationship("RecursoAfectado", secondary="expediente_recurso", back_populates="expedientes")
    radicados_asociados = relationship("RadicadoAsociado", back_populates="expediente", cascade="all, delete-orphan")
    etapa_respuesta = relationship("EtapaRespuesta", back_populates="expediente", cascade="all, delete-orphan")
    etapa_cierre = relationship("EtapaCierre", back_populates="expediente", cascade="all, delete-orphan")
    informes_tecnicos = relationship("InformeTecnico", back_populates="expediente", cascade="all, delete-orphan")
    etapa_acoger_concepto = relationship("EtapaAcogerConcepto", back_populates="expediente", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_expediente_fecha_creacion', 'fecha_creacion'),
        Index('ix_expediente_abogado', 'abogado_responsable_id'),
    )
    