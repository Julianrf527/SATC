from sqlalchemy import Column, Integer, ForeignKey
from .base import Base

class QuejosoExpediente(Base):
    __tablename__ = 'quejoso_expediente'

    quejoso_id = Column(Integer, ForeignKey('quejoso.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
