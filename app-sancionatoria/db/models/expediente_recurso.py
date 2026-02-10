from sqlalchemy import Column, String, Integer, ForeignKey
from .base import Base

class ExpedienteRecurso(Base):
    __tablename__ = "expediente_recurso"

    expediente_radicado  = Column(String, ForeignKey("expediente.radicado", ondelete="SET NULL", onupdate="CASCADE"),primary_key=True)
    recurso_id = Column(Integer, ForeignKey("recurso_afectado.id", ondelete="SET NULL", onupdate="CASCADE"),primary_key=True)