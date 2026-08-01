from sqlalchemy import Column, Integer, ForeignKey
from .base import Base

class ExpedienteTipoAfectacion(Base):
    __tablename__ = 'expediente_tipo_afectacion'

    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
    tipo_afectacion_id = Column(Integer, ForeignKey('tipo_afectacion.id', onupdate="CASCADE", ondelete="CASCADE"), primary_key=True)
