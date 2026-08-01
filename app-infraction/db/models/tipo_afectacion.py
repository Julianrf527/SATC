from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from .base import Base

class TipoAfectacion(Base):
    __tablename__ = 'tipo_afectacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(20), nullable=False)
    recurso_id = Column(Integer, ForeignKey('recurso_afectado.id', onupdate="CASCADE", ondelete="RESTRICT"))

    recurso = relationship("RecursoAfectado", back_populates="tipos_afectacion")
