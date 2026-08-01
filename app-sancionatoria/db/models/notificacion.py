from sqlalchemy import Column, Integer, Date, ForeignKey, Boolean, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Notificacion(Base):
    __tablename__ = 'notificacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', ondelete="CASCADE", onupdate="CASCADE"), index=True)
    numerado = Column(Integer)
    fecha_numerado = Column(Date)
    involucrado_id = Column(Integer, index=True)
    fecha_envio_citacion = Column(Date)
    fecha_constancia_citacion = Column(Date)
    documento_citacion_id = Column(Integer)
    notificacion_exitosa = Column(Boolean)
    fecha_notificacion = Column(Date)
    tipo_notificacion_id = Column(Integer, ForeignKey('tipo_notificacion.id', ondelete="SET NULL", onupdate="CASCADE"))
    documento_notificacion_id = Column(Integer)
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    acto_administrativo = relationship("ActoAdministrativo", back_populates="notificaciones")
    tipo_notificacion = relationship("TipoNotificacion", back_populates="notificaciones")

    __table_args__ = (
        # _acto_con_notif_exitosa (stage.py) filtra exactamente por estas 2 columnas
        # en cada chequeo de "creable" — el query más frecuente de todo el servicio.
        Index("ix_notificacion_acto_exitosa", "acto_administrativo_id", "notificacion_exitosa"),
    )
