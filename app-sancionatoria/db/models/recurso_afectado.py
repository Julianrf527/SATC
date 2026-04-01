from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base

class RecursoAfectado(Base):
    __tablename__ = 'recurso_afectado'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(15), nullable=False)

    expediente_recursos = relationship("ExpedienteRecurso", back_populates="recurso")
