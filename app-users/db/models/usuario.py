from sqlalchemy import Column, BigInteger, String, Boolean, Integer, ForeignKey, TIMESTAMP
from .base import Base
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo

class Usuario(Base):
    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    numero_documento = Column(BigInteger, nullable=False, unique=True)
    primer_nombre = Column(String(20), nullable=False)
    segundo_nombre = Column(String(20))
    primer_apellido = Column(String(20), nullable=False)
    segundo_apellido = Column(String(20))
    correo = Column(String(100), nullable=False, unique=True)
    hash_contrasena = Column(String(255), nullable=False)
    activo = Column(Boolean, default=True)
    fecha_registro = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    # Foreign keys
    rol_id = Column(Integer, ForeignKey("rol.id", ondelete="SET NULL", onupdate="CASCADE"))

    # Relationships
    auditorias = relationship("Auditoria", back_populates="usuario")