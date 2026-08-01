from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base

class ExpedienteRecurso(Base):
    __tablename__ = 'expediente_recurso'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    recurso_id = Column(Integer, ForeignKey('recurso_afectado.id', ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)

    expediente = relationship("Expediente", back_populates="recursos")
    recurso = relationship("RecursoAfectado", back_populates="expediente_recursos")

    __table_args__ = (
        UniqueConstraint('expediente_id', 'recurso_id', name='uq_exp_rec'),
    )
