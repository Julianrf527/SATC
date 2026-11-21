from sqlalchemy import Column, Integer, ForeignKey, Date, TIMESTAMP, Index, String, text
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

# Instancia del acoger concepto: el de la visita técnica (etapa 3) y el de la
# visita de seguimiento (etapa 5). Funcionan igual; a lo sumo una de cada una
# por expediente.
INSTANCIA_VISITA = "VISITA"
INSTANCIA_SEGUIMIENTO = "SEGUIMIENTO"
INSTANCIAS_CONCEPTO = (INSTANCIA_VISITA, INSTANCIA_SEGUIMIENTO)


class EtapaAcogerConcepto(Base):
    __tablename__ = 'etapa_acoger_concepto'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_acogida_concepto = Column(String(30), nullable=False)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    instancia = Column(String(15), nullable=False, default=INSTANCIA_VISITA, server_default=text("'VISITA'"))
    dias_termino = Column(Integer)
    fecha_termino_calculada = Column(Date)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"))
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    expediente = relationship("Expediente", back_populates="etapa_acoger_concepto")
    acto_administrativo = relationship("ActoAdministrativo", back_populates="etapa_acoger_concepto")
    oficio_remite = relationship("OficioRemite", back_populates="etapa_acoger_concepto", uselist=False, cascade="all, delete-orphan")
    solicitud_informacion = relationship("SolicitudInformacion", back_populates="etapa_acoger_concepto", uselist=False, cascade="all, delete-orphan")

    @property
    def es_seguimiento(self) -> bool:
        return self.instancia == INSTANCIA_SEGUIMIENTO

    __table_args__ = (
        Index('ix_etapa_acoger_concepto_expediente', 'expediente_id'),
        Index('uq_etapa_acoger_concepto_instancia', 'expediente_id', 'instancia', unique=True),
    )
