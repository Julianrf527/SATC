from sqlalchemy import Column, Integer, Date, ForeignKey, Text, TIMESTAMP, String, Boolean
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import relationship
from .base import Base

class ActoAdmin(Base):
    __tablename__ = "acto_admin"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numerado = Column(Integer)
    fecha_numerado = Column(Date)
    url_acto = Column(Text)
    fecha_creacion = Column(TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    tipo_acto = Column(String(15))
    etapa_id = Column(Integer, ForeignKey("etapa.id", ondelete="CASCADE", onupdate="CASCADE"))
    nivel_auxiliar = Column(Boolean, nullable=True, default=False)

    notificaciones = relationship(
        "Notificacion",
        back_populates="acto_admin",
        cascade="all, delete-orphan"
    )