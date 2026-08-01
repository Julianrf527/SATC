from sqlalchemy import Column, Integer, String, TIMESTAMP, Text, JSON, ForeignKey
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import relationship
from .base import Base

class AuditoriaDocumento(Base):
    __tablename__ = "auditoria_documentos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, ForeignKey("documentos.id", ondelete="CASCADE"), index=True)
    accion = Column(String(50)) 
    usuario_id = Column(Integer)
    descripcion = Column(Text)
    datos_adicionales = Column(JSON)
    fecha_accion = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )
    ip_address = Column(String(45))

    documento = relationship("Documento", back_populates="auditoria")
