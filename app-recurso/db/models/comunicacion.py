from sqlalchemy import Column, Integer, Date, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Comunicacion(Base):
    __tablename__ = 'comunicacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    numerado = Column(Integer, nullable=False)
    fecha_numerado = Column(Date, nullable=False)
    fecha_envio = Column(Date, nullable=False)
    documento_comunicacion_id = Column(Integer, nullable=False)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="CASCADE"), unique=True, nullable=False)
    # Fecha en que se registró la comunicación (como acto_administrativo.fecha_creacion).
    # NULL solo en filas anteriores a la columna (ver db/migrations.py).
    fecha_creacion = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    acto_administrativo = relationship("ActoAdministrativo", back_populates="comunicacion")
