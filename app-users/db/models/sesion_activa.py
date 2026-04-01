from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, TIMESTAMP, Index
from .base import Base
from datetime import datetime
from zoneinfo import ZoneInfo

class SesionActiva(Base):
    __tablename__  = "sesion_activa"
    __table_args__ = (Index("idx_sesion_usuario_activo", "usuario_id", "activo"),)

    id               = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id       = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    token_jti        = Column(String(255), unique=True, nullable=False)
    ip_address       = Column(String(50))
    user_agent       = Column(Text)
    fecha_login      = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    fecha_ultimo_uso = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    fecha_logout     = Column(TIMESTAMP(timezone=True))
    activo           = Column(Boolean, default=True)

    def is_expired(self, hours: int = 24) -> bool:
        now = datetime.now(ZoneInfo("America/Bogota"))
        return (now - self.fecha_ultimo_uso).total_seconds() > (hours * 3600)
