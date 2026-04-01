from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class MedidaPreventiva(Base):
    __tablename__ = 'medida_preventiva'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_medida_id = Column(Integer, ForeignKey('tipo_medida.id'))
    cantidad = Column(Text)
    especie = Column(Text)
    estado_medida = Column(Boolean)
    etapa_id = Column(Integer, ForeignKey('etapa.id'), unique=True)

    etapa = relationship("Etapa", back_populates="medida_preventiva")
    tipo_medida = relationship("TipoMedida", back_populates="medidas")
