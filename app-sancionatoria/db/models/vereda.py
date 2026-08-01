from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class Vereda(Base):
    __tablename__ = 'vereda'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(25))
    municipio_id = Column(Integer, ForeignKey('municipio.id', onupdate="CASCADE"), index=True)

    municipio = relationship("Municipio", back_populates="veredas")
    expedientes = relationship("Expediente", back_populates="vereda")
