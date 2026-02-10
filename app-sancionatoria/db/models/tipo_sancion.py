from sqlalchemy import Column, Integer, Text
from .base import Base

class TipoSancion(Base):
    __tablename__ = "tipo_sancion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(Text)
