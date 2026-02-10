from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey
from .base import Base

class Etapa(Base):
    __tablename__ = "etapa"

    id = Column(Integer, primary_key=True)
    expediente_radicado = Column(String, ForeignKey("expediente.radicado", ondelete="SET NULL", onupdate="CASCADE"))
    tipo_etapa_id = Column(Integer, ForeignKey("tipo_etapa.id", ondelete="SET NULL", onupdate="CASCADE"))
    fecha_inicio = Column(DateTime)