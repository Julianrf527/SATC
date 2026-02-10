from sqlalchemy import Column, String, Integer
from .base import Base

class RecursoAfectado(Base):
    __tablename__ = "recurso_afectado"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(15))
