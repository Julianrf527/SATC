from sqlalchemy import Column, Integer, String, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base

class RadicadoAsociado(Base):
    __tablename__ = 'radicado_asociado'

    id = Column(Integer, primary_key=True, autoincrement=True)
    radicado = Column(String(15), unique=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)

    expediente = relationship("Expediente", back_populates="radicados_asociados")

    __table_args__ = (
        Index('ix_radicado_asociado_expediente', 'expediente_id'),
    )
