from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, JSON, ForeignKey, TIMESTAMP
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import relationship
from .base import Base

class Auditoria(Base):
    __tablename__    = "auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True)
    expediente_radicado = Column(String(15), nullable=True) # Para facilitar búsquedas sin necesidad de hacer join
    usuario_id = Column(BigInteger, nullable=True, index=True) # Del JWT, bigint en general
    tipo_evento = Column(String(60), nullable=False)
    resultado = Column(String(20), nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    fecha = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")), nullable=False, index=True)
    detalle = Column(Text, nullable=True)
    datos_anteriores = Column(JSON, nullable=True)
    datos_nuevos = Column(JSON, nullable=True)

    expediente = relationship("Expediente")
