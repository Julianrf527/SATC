from sqlalchemy import Column, Integer, Date, ForeignKey, Boolean, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Notificacion(Base):
    __tablename__ = 'notificacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', ondelete="CASCADE", onupdate="CASCADE"))
    numerado = Column(Integer)
    involucrado_id = Column(Integer)
    fecha_numerado = Column(Date)
    fecha_envio_citacion = Column(Date)
    fecha_constancia_citacion = Column(Date)
    documento_citacion_id = Column(Integer)
    notificacion_exitosa = Column(Boolean)
    tipo_notificacion_id = Column(Integer, ForeignKey('tipo_notificacion.id', ondelete="SET NULL", onupdate="CASCADE"))
    fecha_notificacion = Column(Date)
    documento_notificacion_id = Column(Integer)
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    acto_admin = relationship("ActoAdministrativo", back_populates="notificaciones")
    tipo_notificacion = relationship("TipoNotificacion", back_populates="notificaciones")
