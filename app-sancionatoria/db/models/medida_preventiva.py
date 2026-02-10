from sqlalchemy import Column, Integer, Text, ForeignKey, Boolean
from .base import Base

class MedidaPreventiva(Base):
    __tablename__ = "medida_preventiva"

    id = Column(Integer, primary_key=True)
    tipo_medida_id = Column(Integer, ForeignKey("tipo_medida.id", ondelete="SET NULL", onupdate="CASCADE"))
    cantidad = Column(Text)
    especie = Column(Text)
    estado_medida = Column(Boolean)
    etapa_id = Column(Integer, ForeignKey("etapa.id", ondelete="SET NULL", onupdate="CASCADE"))
