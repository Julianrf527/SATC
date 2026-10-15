from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from .base import Base
from .enums import uso_agua_enum

class ExpedienteUso(Base):
    __tablename__ = 'expediente_uso'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    uso = Column(uso_agua_enum, nullable=False)

    expediente = relationship("Expediente", back_populates="usos")

    __table_args__ = (
        UniqueConstraint('expediente_id', 'uso', name='uq_exp_uso'),
        Index('ix_expediente_uso_uso', 'uso'),
    )
