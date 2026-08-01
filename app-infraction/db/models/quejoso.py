from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from .base import Base

class Quejoso(Base):
    __tablename__ = 'quejoso'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(150), nullable=True)
    telefono = Column(String(10), nullable=True)
    correo = Column(String(100), nullable=True)
    anonimo = Column(Boolean, default=False, nullable=False)

    expedientes = relationship("Expediente", secondary="quejoso_expediente", back_populates="quejosos")
