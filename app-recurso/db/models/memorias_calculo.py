from sqlalchemy import Column, Integer, String, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from .base import Base, VersionadoMixin

class MemoriasCalculo(VersionadoMixin, Base):
    __tablename__ = 'memorias_calculo'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), unique=True, nullable=False)
    radicado = Column(String(15), unique=True, nullable=False)
    fecha_radicado = Column(Date, nullable=False)
    doc_planos_id = Column(Integer, nullable=False)
    concepto_tecnico_id = Column(Integer, ForeignKey('concepto_tecnico.id', onupdate="CASCADE"), unique=True)
    requerimiento_id = Column(Integer, ForeignKey('requerimiento.id', onupdate="CASCADE"), unique=True)
    subsanacion_id = Column(Integer, ForeignKey('subsanacion.id', onupdate="CASCADE"), unique=True)
    # id en app-users (otra BD): FK lógica, sin constraint.
    encargado_acto_id = Column(Integer)
    acto_admin_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"), unique=True)

    expediente = relationship("Expediente", back_populates="memorias_calculo")
    concepto_tecnico = relationship("ConceptoTecnico")
    requerimiento = relationship("Requerimiento")
    subsanacion = relationship("Subsanacion")
    acto_administrativo = relationship("ActoAdministrativo")

    __table_args__ = (
        Index('ix_memorias_calculo_encargado', 'encargado_acto_id'),
    )
