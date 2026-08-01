from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import Base

class ExpedienteInvolucrado(Base):
    __tablename__ = 'expediente_involucrado'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    involucrado_id = Column(Integer, nullable=False)

    expediente = relationship("Expediente", back_populates="involucrados")

    __table_args__ = (
        UniqueConstraint('expediente_id', 'involucrado_id', name='uq_exp_inv'),
    )
