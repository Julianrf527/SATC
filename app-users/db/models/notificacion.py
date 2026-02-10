from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, String
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Notificacion(Base):
    __tablename__ = "notificacion"

    id = Column(Integer, primary_key=True)
    mensaje = Column(Text, nullable=False)
    id_vinculada = Column(String(20), nullable=False)
    tipo = Column(String(20), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuario.numero_documento", ondelete="SET NULL", onupdate="CASCADE"))
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=datetime.now(ZoneInfo("America/Bogota")))
