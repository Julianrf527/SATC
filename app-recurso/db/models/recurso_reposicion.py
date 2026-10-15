from sqlalchemy import Column, Integer, String, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from .base import Base, VersionadoMixin
from .enums import resultado_recurso_enum

class RecursoReposicion(VersionadoMixin, Base):
    __tablename__ = 'recurso_reposicion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    decision_id = Column(Integer, ForeignKey('decision.id', onupdate="CASCADE", ondelete="CASCADE"), unique=True)
    # id en app-users (otra BD): FK lógica, sin constraint.
    encargado_acto_id = Column(Integer)
    acto_admin_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"), unique=True)
    radicado = Column(String(15), nullable=False)
    fecha_radicado = Column(Date, nullable=False)
    resultado = Column(resultado_recurso_enum)
    doc_recurso_id = Column(Integer, nullable=False)

    decision = relationship("Decision", back_populates="recurso_reposicion")
    acto_administrativo = relationship("ActoAdministrativo")

    __table_args__ = (
        Index('ix_recurso_reposicion_encargado', 'encargado_acto_id'),
    )
