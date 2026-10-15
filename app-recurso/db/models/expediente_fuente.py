from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Index
from .base import Base

class ExpedienteFuente(Base):
    __tablename__ = 'expediente_fuente'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    fuente_id = Column(Integer, ForeignKey('fuente.id', onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)

    __table_args__ = (
        UniqueConstraint('expediente_id', 'fuente_id', name='uq_exp_fuente'),
        Index('ix_expediente_fuente_fuente', 'fuente_id'),
    )
