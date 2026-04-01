from sqlalchemy import Column, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class DecisionFondo(Base):
    __tablename__ = 'decision_fondo'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_sancion_id = Column(Integer, ForeignKey('tipo_sancion.id'))
    detalle = Column(Text)
    etapa_id = Column(Integer, ForeignKey('etapa.id'), unique=True)

    etapa = relationship("Etapa", back_populates="decision_fondo")
    tipo_sancion = relationship("TipoSancion", back_populates="decisiones")
