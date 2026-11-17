from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base

class TipoFuente(Base):
    __tablename__ = 'tipo_fuente'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(20), nullable=False, unique=True)

    expedientes = relationship("Expediente", back_populates="tipo_fuente")
