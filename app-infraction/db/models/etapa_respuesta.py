from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from .base import Base

class EtapaRespuesta(Base):
    __tablename__ = 'etapa_respuesta'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    radicado = Column(String(15), unique=True)
    fecha_radicado = Column(Date)
    documento_radicado_id = Column(Integer)
    require_medida_preventiva = Column(Boolean)
    fecha_creacion = Column(Date)

    expediente = relationship("Expediente", back_populates="etapa_respuesta")

    __table_args__ = (
        Index('ix_etapa_respuesta_expediente', 'expediente_id'),
        Index('ix_etapa_respuesta_fecha', 'fecha_radicado'),
    )
