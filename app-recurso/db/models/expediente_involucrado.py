from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Index, TIMESTAMP, text
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base, VersionadoMixin
from .enums import TipoVinculo, tipo_vinculo_enum

class ExpedienteInvolucrado(VersionadoMixin, Base):
    __tablename__ = 'expediente_involucrado'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), nullable=False)
    # id en app-involved (otra BD): FK lógica, sin constraint.
    involucrado_id = Column(Integer, nullable=False)
    tipo_vinculo = Column(
        tipo_vinculo_enum, nullable=False,
        default=TipoVinculo.SOLICITANTE, server_default=text("'SOLICITANTE'"),
    )
    # app-involved. Obligatorio si el involucrado tiene tipo de documento NIT (V14).
    representante_id = Column(Integer)
    # Solo TERCERO_INTERVINIENTE: acto que lo reconoce; NULL hasta que se expida.
    acto_admin_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"), unique=True)
    fecha_vinculacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    expediente = relationship("Expediente", back_populates="involucrados")
    acto_administrativo = relationship("ActoAdministrativo")

    __table_args__ = (
        UniqueConstraint('expediente_id', 'involucrado_id', name='uq_exp_inv'),
        Index('ix_expediente_involucrado_involucrado', 'involucrado_id'),
    )
