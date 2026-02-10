from sqlalchemy import Column, Integer, ForeignKey, TIMESTAMP, String, Boolean
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import relationship
from .base import Base

class AsignacionRevisor(Base):
    __tablename__ = "asignaciones_revisores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    documento_id = Column(Integer, ForeignKey("documentos.id", ondelete="CASCADE"))
    revisor_id = Column(Integer)
    fecha_asignacion = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )
    notificado = Column(Boolean)

    # Relación inversa actualizada
    documento = relationship("Documento", back_populates="asignaciones_revisores")
