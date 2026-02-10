from sqlalchemy import Column, Integer, BigInteger, String, ForeignKey, JSON, TIMESTAMP, Text
from .base import Base
from datetime import datetime
from zoneinfo import ZoneInfo

class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, autoincrement=True, primary_key=True)
    tabla_afectada = Column(String(30), nullable=True)
    id_registro = Column(String(20), nullable=True)
    tipo_operacion = Column(String(10), nullable=False)
    usuario_id = Column(BigInteger, ForeignKey("usuario.numero_documento", ondelete="SET NULL", onupdate="CASCADE"))
    fecha = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )
    descripcion = Column(Text)
    datos_anteriores = Column(JSON)
    datos_nuevos = Column(JSON)
