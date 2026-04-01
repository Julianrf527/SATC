from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base

class TipoEtapa(Base):
    __tablename__ = 'tipo_etapa'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(30), unique=True)

    etapas = relationship("Etapa", back_populates="tipo_etapa")
