from sqlalchemy import Column, Integer, ForeignKey, Text, TIMESTAMP, String
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import relationship
from .base import Base

class Revision(Base):
    __tablename__ = "revisiones"

    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, ForeignKey("documentos.id", ondelete="CASCADE"), index=True)
    version_revisada = Column(Integer)
    revisor_id = Column(Integer, index=True)
    estado_revision = Column(String(20))
    comentarios = Column(Text)
    fecha_revision = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )

    documento = relationship("Documento", back_populates="revisiones")