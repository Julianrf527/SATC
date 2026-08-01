from sqlalchemy import Column, Integer, ForeignKey, String, TIMESTAMP, BigInteger, Text
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import relationship
from .base import Base

class VersionDocumento(Base):
    __tablename__ = "versiones_documento"

    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, ForeignKey("documentos.id", ondelete="CASCADE"), index=True)
    numero_version = Column(Integer)
    archivo_url = Column(String(500))
    archivo_nombre_original = Column(String(255))
    archivo_size = Column(BigInteger)
    usuario_subida_id = Column(Integer)
    fecha_subida = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )
    comentario = Column(Text)

    documento = relationship("Documento", back_populates="versiones")
