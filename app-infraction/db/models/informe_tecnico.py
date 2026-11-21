from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import TIMESTAMP, Column, Integer, String, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from .base import Base

class InformeTecnico(Base):
    __tablename__ = 'informe_tecnico'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    profesional_asignado_id = Column(Integer)
    revisor_asignado_id = Column(Integer)
    modo = Column(String(10), nullable=False, default='FLUJO', server_default='FLUJO')
    fecha_programacion_visita = Column(Date)
    fecha_recibido_informe = Column(Date)
    fecha_aceptacion_informe = Column(Date)
    # Día en que quedó por primera vez con técnico Y fecha de programación
    # (inicio de la alerta de primera versión; reasignar no la cambia).
    fecha_asignacion = Column(Date)
    documento_informe_id = Column(Integer)
    tipo_informe = Column(String(20))
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    expediente = relationship("Expediente", back_populates="informes_tecnicos")

    __table_args__ = (
        Index('ix_informe_tecnico_expediente', 'expediente_id'),
        Index('ix_informe_tecnico_profesional', 'profesional_asignado_id'),  # fixed: was 'profesional_asignado'
    )
