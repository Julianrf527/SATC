from sqlalchemy import Column, Integer, Date, ForeignKey, String, Boolean, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class ActoAdministrativo(Base):
    __tablename__ = 'acto_administrativo'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_acto = Column(String(15))
    numerado = Column(Integer)
    fecha_numerado = Column(Date)
    documento_acto_id = Column(Integer)
    etapa_id = Column(Integer, ForeignKey('etapa.id', ondelete="CASCADE", onupdate="CASCADE"))
    nivel_auxiliar = Column(Boolean, default=False)
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    etapa = relationship("Etapa", back_populates="actos_administrativos")
    notificaciones = relationship("Notificacion", back_populates="acto_admin", cascade="all, delete-orphan")
    comunicaciones = relationship("Comunicacion", back_populates="acto_admin", cascade="all, delete-orphan")
