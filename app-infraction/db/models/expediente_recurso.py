from sqlalchemy import Column, Integer, ForeignKey
from .base import Base

class ExpedienteRecurso(Base):
    __tablename__ = 'expediente_recurso'

    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    recurso_id = Column(Integer, ForeignKey('recurso_afectado.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
