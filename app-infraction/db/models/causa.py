from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base

class Causa(Base):
    __tablename__ = 'causa'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(20), nullable=False)

    expedientes = relationship("Expediente", back_populates="causa")
