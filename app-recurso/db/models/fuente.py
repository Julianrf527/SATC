from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base

class Fuente(Base):
    """Clase de fuente: NACIMIENTO, QUEBRADA, RÍO… (seed §3.1)."""
    __tablename__ = 'fuente'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(30), nullable=False, unique=True)

    expedientes = relationship("Expediente", secondary="expediente_fuente", back_populates="fuentes")
