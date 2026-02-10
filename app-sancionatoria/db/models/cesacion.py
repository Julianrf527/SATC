from sqlalchemy import Column, Integer, Text, ForeignKey
from .base import Base

class Cesacion(Base):
    __tablename__ = "cesacion"

    id = Column(Integer, primary_key=True)
    tipo_cesacion_id = Column(Integer, ForeignKey("etapa.id", ondelete="SET NULL", onupdate="CASCADE"))
    etapa_id = Column(Integer, ForeignKey("etapa.id", ondelete="SET NULL", onupdate="CASCADE"))
