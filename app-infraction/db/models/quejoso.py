from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base

class Quejoso(Base):
    __tablename__ = 'quejoso'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(150))
    telefono = Column(String(10))
    correo = Column(String(100))

    expedientes = relationship("Expediente", secondary="quejoso_expediente", back_populates="quejosos")
