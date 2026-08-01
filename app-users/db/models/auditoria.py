from sqlalchemy import Column, Integer, String, ForeignKey, JSON, TIMESTAMP, Text, BigInteger, DateTime
from .base import Base
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo

class Auditoria(Base):
    __tablename__    = "auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id", ondelete="SET NULL"), nullable=True, index=True)
    tipo_evento = Column(String(30), nullable=False)
    resultado = Column(String(10), nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    # Se filtra y ordena por fecha en /user/log; index para evitar full scan + sort.
    fecha = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")), nullable=False, index=True)
    detalle = Column(Text, nullable=True)
    datos_anteriores = Column(JSON, nullable=True)
    datos_nuevos = Column(JSON, nullable=True)

    usuario = relationship("Usuario", back_populates="auditorias")
