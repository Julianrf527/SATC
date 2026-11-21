from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from .base import Base

class SolicitudInformacion(Base):
    __tablename__ = 'solicitud_informacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    etapa_acoger_concepto_id = Column(Integer, ForeignKey('etapa_acoger_concepto.id', onupdate="CASCADE", ondelete="CASCADE"), unique=True, nullable=False)
    radicado = Column(String(11), nullable=False)
    fecha_radicado = Column(String(10), nullable=False)
    archivo_solicitud_id = Column(Integer, nullable=False)
    # Respuesta del usuario a la solicitud (opcional; si se registra, van los tres).
    radicado_respuesta = Column(String(11), nullable=True)
    fecha_radicado_respuesta = Column(String(10), nullable=True)
    archivo_respuesta_id = Column(Integer, nullable=True)

    etapa_acoger_concepto = relationship("EtapaAcogerConcepto", back_populates="solicitud_informacion")
