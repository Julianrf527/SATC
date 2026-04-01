from sqlalchemy import Column, Integer, Text
from sqlalchemy.orm import relationship
from .base import Base

class TipoCesacion(Base):
    __tablename__ = 'tipo_cesacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(Text)

    cesaciones = relationship("Cesacion", back_populates="tipo_cesacion")
