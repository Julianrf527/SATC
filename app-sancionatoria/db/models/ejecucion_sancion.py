from sqlalchemy import Column, Integer, Text, ForeignKey, Boolean, Date
from .base import Base

class EjecucionSancion(Base):
    __tablename__ = "ejecucion_sancion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cobro_coactivo = Column(Boolean)
    disposicion = Column(Boolean)
    ruia = Column(Boolean)
    etapa_id = Column(Integer, ForeignKey("etapa.id", ondelete="SET NULL", onupdate="CASCADE"))
    auto_admin = Column(Text)
    fecha_auto = Column(Date)
    cobro_coactivo_doc_url = Column(Text)
    ruia_doc_url = Column(Text)
    auto_doc_url= Column(Text)
    memorando = Column(Boolean)
    memorando_doc_url = Column(Text)
