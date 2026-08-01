from sqlalchemy import Column, Integer, Date, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Comunicacion(Base):
    __tablename__ = 'comunicacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    numerado = Column(Integer)
    fecha_numerado = Column(Date)
    fecha_envio = Column(Date)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id'))
    documento_comunicacion_id = Column(Integer)
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    acto_admin = relationship("ActoAdministrativo", back_populates="comunicacion")
