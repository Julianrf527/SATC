from sqlalchemy import Column, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class FormulacionCargos(Base):
    __tablename__ = 'formulacion_cargos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    descargos = Column(Boolean)
    etapa_id = Column(Integer, ForeignKey('etapa.id'), unique=True)
    documento_id = Column(Integer)

    etapa = relationship("Etapa", back_populates="formulacion_cargos")
