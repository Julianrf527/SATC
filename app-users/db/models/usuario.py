from sqlalchemy import Column, BigInteger, String, Boolean, DateTime, Integer, ForeignKey, TIMESTAMP
from .base import Base
from datetime import datetime
from zoneinfo import ZoneInfo

class Usuario(Base):
    __tablename__ = "usuario"

    numero_documento = Column(BigInteger, primary_key=True)
    primer_nombre = Column(String(50), nullable=False)
    segundo_nombre = Column(String(50))
    primer_apellido = Column(String(50), nullable=False)
    segundo_apellido = Column(String(50))
    correo = Column(String(100), unique=True)
    hash_contrasena = Column(String, nullable=False)
    activo = Column(Boolean, default=True)
    ultimo_ingreso = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    rol_id = Column(Integer, ForeignKey("rol.id", ondelete="SET NULL", onupdate="CASCADE"))
    fecha_registro = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))