from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import relationship
from .base import Base


class Auditoria(Base):
    """Registro de auditoría (copia de app-infraction). Lo escribe utils/log.insert_log."""
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    # Radicado del expediente: para buscar sin join.
    expediente_radicado = Column(String(15), nullable=True)
    usuario_id = Column(Integer, nullable=True)
    tipo_evento = Column(String(30), nullable=False)
    resultado = Column(String(10), nullable=False)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    fecha = Column(DateTime(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")), nullable=False)
    detalle = Column(Text, nullable=True)
    datos_anteriores = Column(JSON, nullable=True)
    datos_nuevos = Column(JSON, nullable=True)

    expediente = relationship("Expediente")
