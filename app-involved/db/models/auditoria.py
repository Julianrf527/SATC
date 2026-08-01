from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, JSON, Index
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(BigInteger, nullable=True) # Del JWT, bigint en general
    tipo_evento = Column(String(30), nullable=False)
    resultado = Column(String(10), nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    fecha = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")), nullable=False)
    detalle = Column(Text, nullable=True)
    datos_anteriores = Column(JSON, nullable=True)
    datos_nuevos = Column(JSON, nullable=True)

    __table_args__ = (
        # GET /involved/log ordena siempre por fecha desc y filtra por estas columnas.
        Index("ix_auditoria_fecha", "fecha"),
        Index("ix_auditoria_usuario_id", "usuario_id"),
        Index("ix_auditoria_tipo_evento", "tipo_evento"),
    )
