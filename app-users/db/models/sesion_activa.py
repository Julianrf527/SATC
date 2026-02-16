from sqlalchemy import Column, Integer, BigInteger, String, Text, Boolean, ForeignKey, TIMESTAMP, Index
from .base import Base
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

class SesionActiva(Base):
    __tablename__ = "sesion_activa"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(BigInteger, ForeignKey("usuario.numero_documento", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    token_jti = Column(String(255), unique=True, nullable=False)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    fecha_login = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    fecha_ultimo_uso = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    activo = Column(Boolean, default=True)
    
    # Índice compuesto para optimizar UPDATE en login concurrente
    __table_args__ = (
        Index('idx_sesion_usuario_activo', 'usuario_id', 'activo'),
    )
    
    def is_expired(self, hours: int = 24) -> bool:
        """Verifica si la sesión ha expirado (default: 24 horas)"""
        now = datetime.now(ZoneInfo("America/Bogota"))
        return (now - self.fecha_ultimo_uso).total_seconds() > (hours * 3600)
