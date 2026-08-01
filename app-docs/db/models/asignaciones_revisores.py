from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, String, Boolean
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import relationship
from .base import Base

class AsignacionRevisor(Base):
    __tablename__ = "asignaciones_revisores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, ForeignKey("documentos.id", ondelete="CASCADE"), index=True)
    revisor_id = Column(Integer, index=True)
    fecha_asignacion = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )
    notificado = Column(Boolean)

    documento = relationship("Documento", back_populates="asignaciones_revisores")
