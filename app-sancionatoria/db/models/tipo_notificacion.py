from sqlalchemy import Column, Integer, String
from .base import Base

class TipoNotificacion(Base):
    __tablename__ = "tipo_notificacion"

    id = Column(Integer, primary_key=True)
    nombre  = Column(String(15))
