from sqlalchemy import Boolean, Column, DateTime, Integer, String, ForeignKey, Date, Index, func, text
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
    requiere_pruebas = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    # Cuándo se registró el recurso en el sistema (inicio de los plazos en días
    # calendario de las alertas). ``fecha_radicado`` es la fecha del escrito del usuario.
    fecha_creacion = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    decision = relationship("Decision", back_populates="recurso_reposicion")
    acto_administrativo = relationship("ActoAdministrativo")
    practica_pruebas = relationship("PracticaPruebas", back_populates="recurso", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_recurso_reposicion_encargado', 'encargado_acto_id'),
    )
