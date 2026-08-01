from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from .base import Base

class TipoNotificacion(Base):
    __tablename__ = 'tipo_notificacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(15), nullable=False)

    notificaciones = relationship("Notificacion", back_populates="tipo_notificacion")
