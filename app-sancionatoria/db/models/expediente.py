from sqlalchemy import Column, TIMESTAMP, Integer, String, BigInteger, ForeignKey, Identity, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class Expediente(Base):
    __tablename__ = "expediente"

    radicado = Column(String(10), primary_key=True)
    id_auxiliar = Column(
                        BigInteger,
                        Identity(always=True),
                        unique=True,
                        nullable=False
                    )
    nombre_expediente = Column(String(7))
    motivo_afectacion = Column(String(200))
    fecha_creacion = Column(TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    encargado_id = Column(
        BigInteger
    )
    direccion = Column(String(100))
    vereda_id = Column(Integer, ForeignKey("vereda.id", ondelete="SET NULL", onupdate="CASCADE"))
    archivado = Column(Boolean, nullable=True, default=False)
    fecha_archivado = Column(TIMESTAMP(timezone=True), default=lambda: datetime.now(ZoneInfo("America/Bogota")), nullable=True)
    # Relación con involucrados
    involucrados = relationship(
        "InvolucradoExpediente",
        back_populates="expediente",
        cascade="all, save-update",
        passive_updates=False
    )