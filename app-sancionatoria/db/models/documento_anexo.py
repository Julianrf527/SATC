from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class DocumentoAnexo(Base):
    __tablename__ = 'documento_anexo'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(100))
    documento_anexo_id = Column(Integer)
    etapa_id = Column(Integer, ForeignKey('etapa.id'))

    etapa = relationship("Etapa", back_populates="anexos")
