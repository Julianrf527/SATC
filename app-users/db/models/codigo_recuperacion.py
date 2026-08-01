from sqlalchemy import Column, String, Integer, ForeignKey, TIMESTAMP, UniqueConstraint
from .base import Base
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

class CodigoRecuperacion(Base):
    __tablename__    = "codigo_recuperacion"
    __table_args__   = (UniqueConstraint("usuario_id", name="uq_codigo_usuario"),)

    id                = Column(Integer, primary_key=True, autoincrement=True)
    codigo            = Column(String(60), nullable=False)
    fecha_expiracion  = Column(TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(ZoneInfo("America/Bogota")) + timedelta(minutes=10))
    fecha_creacion    = Column(TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    usuario_id        = Column(Integer, ForeignKey("usuario.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    intentos_fallidos = Column(Integer, default=0)
