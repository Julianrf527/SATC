from sqlalchemy import Column, Integer, String, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from .base import Base

class InformeTecnico(Base):
    __tablename__ = 'informe_tecnico'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    profesional_asignado = Column(Integer)
    fecha_programacion_visita = Column(Date)
    fecha_recibido_informe = Column(Date)
    fecha_entrega_informe = Column(Date)
    documento_informe_id = Column(Integer)
    tipo_informe = Column(String(20))

    expediente = relationship("Expediente", back_populates="informes_tecnicos")

    __table_args__ = (
        Index('ix_informe_tecnico_expediente', 'expediente_id'),
        Index('ix_informe_tecnico_profesional', 'profesional_asignado'),
    )
