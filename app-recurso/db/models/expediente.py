from sqlalchemy import Column, Integer, String, ForeignKey, Date, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base, VersionadoMixin

class Expediente(VersionadoMixin, Base):
    __tablename__ = 'expediente'

    id = Column(Integer, primary_key=True, autoincrement=True)
    radicado = Column(String(15), unique=True, nullable=False)
    fecha_radicado = Column(Date, nullable=False)
    # Identificador del expediente, p. ej. "CA 001-26".
    expediente = Column(String(9), unique=True, nullable=False)
    numero_vital = Column(String(20), nullable=False)
    nombre_predio = Column(String(50), nullable=False)
    matricula_inmobiliaria = Column(String(20), nullable=False)
    codigo_catastral = Column(String(30), nullable=False)
    # Radicado de la solicitud; su documento es doc_comprobante_pago_id.
    radicado_oficio_entrada = Column(String(20), nullable=False)
    fecha_oficio_entrada = Column(Date, nullable=False)
    # Los doc_*_id de toda la app son ids de file_hash en app-docs (otra BD):
    # FK lógica, sin constraint.
    doc_comprobante_pago_id = Column(Integer, nullable=False)
    vereda_id = Column(Integer, ForeignKey('vereda.id', onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    tipo_fuente_id = Column(Integer, ForeignKey('tipo_fuente.id', onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    # Nombre propio de la fuente (input libre), p. ej. "Juancho Castro".
    nombre_fuente = Column(String(50), nullable=False)
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    vereda = relationship("Vereda", back_populates="expedientes")
    tipo_fuente = relationship("TipoFuente", back_populates="expedientes")
    fuentes = relationship("Fuente", secondary="expediente_fuente", back_populates="expedientes")
    usos = relationship("ExpedienteUso", back_populates="expediente", cascade="all, delete-orphan")
    involucrados = relationship("ExpedienteInvolucrado", back_populates="expediente", cascade="all, delete-orphan")
    acto_admite = relationship("ActoAdmite", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    concepto_tecnico = relationship("ConceptoTecnico", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    requerimiento = relationship("Requerimiento", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    decision = relationship("Decision", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    memorias_calculo = relationship("MemoriasCalculo", back_populates="expediente", uselist=False, cascade="all, delete-orphan")
    recibo_satisfaccion_obras = relationship("ReciboSatisfaccionObras", back_populates="expediente", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_expediente_numero_vital', 'numero_vital'),
        Index('ix_expediente_vereda', 'vereda_id'),
        Index('ix_expediente_tipo_fuente', 'tipo_fuente_id'),
        Index('ix_expediente_fecha_radicado', 'fecha_radicado'),
    )
