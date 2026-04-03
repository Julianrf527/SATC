from sqlalchemy import Column, Integer, Boolean, ForeignKey, Date, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Notificacion(Base):
    __tablename__ = 'notificacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha_creacion = Column(Date)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    numerado = Column(Integer)
    fecha_numerado = Column(Date)
    involucrado_id = Column(Integer, nullable=False)
    fecha_envio_citacion = Column(Date)
    fecha_constancia_citacion = Column(Date)
    documento_citacion_id = Column(Integer)
    notificacion_exitosa = Column(Boolean)
    fecha_notificacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    tipo_notificacion_id = Column(Integer, ForeignKey('tipo_notificacion.id', onupdate="CASCADE", ondelete="RESTRICT"))
    documento_notificacion_id = Column(Integer)

    acto_administrativo = relationship("ActoAdministrativo", back_populates="notificaciones")
    tipo_notificacion = relationship("TipoNotificacion", back_populates="notificaciones")

    __table_args__ = (
        Index('ix_notificacion_acto', 'acto_administrativo_id'),
        Index('ix_notificacion_fecha_notificacion', 'fecha_notificacion'),
    )
