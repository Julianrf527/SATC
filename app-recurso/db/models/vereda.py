from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base

class Vereda(Base):
    __tablename__ = 'vereda'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(25), nullable=False)
    municipio_id = Column(Integer, ForeignKey('municipio.id', onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)

    municipio = relationship("Municipio", back_populates="veredas")
    expedientes = relationship("Expediente", back_populates="vereda")

    __table_args__ = (
        UniqueConstraint('municipio_id', 'nombre', name='uq_vereda_municipio_nombre'),
    )
