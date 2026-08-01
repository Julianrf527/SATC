from sqlalchemy import Column, Integer, Text, ForeignKey, TIMESTAMP, String, Boolean
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Notificacion(Base):
    __tablename__  = "notificacion"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    mensaje        = Column(Text, nullable=False)
    id_vinculada   = Column(String(20))
    usuario_id     = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    tipo           = Column(String(15))
    leida          = Column(Boolean, default=False)
    fecha_leida    = Column(TIMESTAMP(timezone=True))
