from sqlalchemy import Column, Integer, Date, ForeignKey, Text
from sqlalchemy.orm import relationship
from .base import Base

class Notificacion(Base):
    __tablename__ = "notificacion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha_creacion = Column(Date)
    acto_admin_id = Column(Integer, ForeignKey("acto_admin.id", ondelete="CASCADE", onupdate="CASCADE"))

    acto_admin = relationship("ActoAdmin", back_populates="notificaciones")

    involucrados = relationship(
    "InvolucradoNotificacion",
    back_populates="notificacion",
    cascade="all, delete-orphan"
)