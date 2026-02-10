from sqlalchemy import Column, Integer, Text, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class InvolucradoNotificacion(Base):
    __tablename__ = "involucrado_notificacion"

    id = Column(Integer, primary_key=True, index=True)
    numerado = Column(Integer)
    fecha_numerado = Column(Date)
    notificacion_id = Column(Integer, ForeignKey("notificacion.id", ondelete="SET NULL", onupdate="CASCADE"))
    involucrado_id = Column(Integer, ForeignKey("involucrado.id", ondelete="SET NULL", onupdate="CASCADE"))
    fecha_envio_citacion = Column(Date)
    fecha_constancia_citacion = Column(Date)
    url_documento = Column(Text)
    notificacion_exitosa = Column(Boolean)
    fecha_notificacion = Column(Date)
    tipo_notificacion_id = Column(Integer, ForeignKey("tipo_notificacion.id", ondelete="SET NULL", onupdate="CASCADE"))


    notificacion = relationship("Notificacion", back_populates="involucrados")