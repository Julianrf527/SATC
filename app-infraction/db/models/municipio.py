from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base

class Municipio(Base):
    __tablename__ = 'municipio'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(30), nullable=False)

    veredas = relationship("Vereda", back_populates="municipio")
