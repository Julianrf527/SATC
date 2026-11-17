from sqlalchemy import Column, Integer, Boolean, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from .base import Base, VersionadoMixin
from .enums import tipo_decision_enum

class Decision(VersionadoMixin, Base):
    __tablename__ = 'decision'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), unique=True, nullable=False)
    # app-users. Abogado que se asignó ("Asignarme para diligenciar"). NULL solo en
    # cargue histórico de super gestión sin encargado (desviación del DBML).
    encargado_acto_id = Column(Integer)
    # Se llena al numerar el acto.
    acto_admin_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"), unique=True)
    decision = Column(tipo_decision_enum)
    requiere_memorias = Column(Boolean)
    fecha_ejecutoria = Column(Date)

    expediente = relationship("Expediente", back_populates="decision")
    acto_administrativo = relationship("ActoAdministrativo")
    recurso_reposicion = relationship("RecursoReposicion", back_populates="decision", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_decision_encargado', 'encargado_acto_id'),
        Index('ix_decision_decision', 'decision'),
    )
