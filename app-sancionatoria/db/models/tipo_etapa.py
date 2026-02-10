from sqlalchemy import Column, Integer, String
from .base import Base

class TipoEtapa(Base):
    __tablename__ = "tipo_etapa"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(30))
