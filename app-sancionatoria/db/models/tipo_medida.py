from sqlalchemy import Column, Integer, Text
from .base import Base

class TipoMedida(Base):
    __tablename__ = 'tipo_medida'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(Text)
