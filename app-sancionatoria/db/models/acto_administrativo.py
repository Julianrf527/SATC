from sqlalchemy import Column, Integer, Date, String, TIMESTAMP
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
    documento_acto_administrativo_id = Column(Integer)  # ref → app-docs
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    # Cada tabla de etapa referencia al acto vía su propia FK acto_administrativo_id.

    notificaciones = relationship("Notificacion", back_populates="acto_administrativo", cascade="all, delete-orphan")
    comunicaciones = relationship("Comunicacion", back_populates="acto_admin", cascade="all, delete-orphan")
