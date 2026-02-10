from sqlalchemy import Column, Integer, Date, ForeignKey, Text, String, TIMESTAMP
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Documento(Base):
    __tablename__ = "documento"

    id = Column(Integer, autoincrement=True, primary_key=True)
    nombre = Column(String(100))
    url_documento = Column(Text)
    fecha_subida = Column(TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    etapa_id = Column(Integer, ForeignKey("etapa.id", ondelete="SET NULL", onupdate="CASCADE"))