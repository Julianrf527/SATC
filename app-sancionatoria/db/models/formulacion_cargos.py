from sqlalchemy import Column, Integer, ForeignKey, Boolean, Text
from .base import Base

class FormulacionCargos(Base):
    __tablename__ = "formulacion_cargos"

    id = Column(Integer, primary_key=True)
    descargos = Column(Boolean)
    url_documento = Column(Text)
    etapa_id = Column(Integer, ForeignKey("etapa.id", ondelete="SET NULL", onupdate="CASCADE"))
