from sqlalchemy import Column, Integer, Date, ForeignKey, Text
from .base import Base

class Comunicacion(Base):
    __tablename__ = "comunicacion"

    id = Column(Integer, autoincrement=True, primary_key=True)
    numerado = Column(Integer)
    fecha_numerado = Column(Date)
    fecha_envio = Column(Date)
    fecha_creacion = Column(Date)
    url_documento = Column(Text)
    acto_admin_id = Column(Integer, ForeignKey("acto_admin.id", ondelete="SET NULL", onupdate="CASCADE"))