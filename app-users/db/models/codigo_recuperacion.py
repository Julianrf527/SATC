from sqlalchemy import Column, String,Integer, BigInteger, ForeignKey, TIMESTAMP
from .base import Base
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

class CodigoRecuperacion(Base):
    __tablename__ = "codigo_recuperacion"

    id = Column(Integer, primary_key=True)
    codigo = Column(String(60))
    fecha_expiracion = Column(TIMESTAMP(timezone=True), default= lambda: datetime.now(ZoneInfo("America/Bogota")) + timedelta(minutes=10))
    usuario_id = Column(BigInteger, ForeignKey("usuario.numero_documento", ondelete="SET NULL", onupdate="CASCADE"))