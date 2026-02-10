from sqlalchemy import Column, Integer, Text
from .base import Base

class TipoCesacion(Base):
    __tablename__ = "tipo_cesacion"

    id = Column(Integer, primary_key=True)
    nombre  = Column(Text)
