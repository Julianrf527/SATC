from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class Cesacion(Base):
    __tablename__ = 'cesacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_cesacion_id = Column(Integer, ForeignKey('tipo_cesacion.id'))
    etapa_id = Column(Integer, ForeignKey('etapa.id'), unique=True)

    etapa = relationship("Etapa", back_populates="cesacion")
    tipo_cesacion = relationship("TipoCesacion", back_populates="cesaciones")
