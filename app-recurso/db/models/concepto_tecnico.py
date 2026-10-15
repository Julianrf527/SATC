from sqlalchemy import Column, Integer, Boolean, Float, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from .base import Base, VersionadoMixin

class ConceptoTecnico(VersionadoMixin, Base):
    """``expediente_id`` solo cuando es la etapa 2; como sub-proceso
    (adicional, memorias, subsanación, obras) queda NULL y lo referencia el padre."""
    __tablename__ = 'concepto_tecnico'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), unique=True)
    fecha_visita_tecnica = Column(Date)
    # app-users con permiso recurso_tecnico. Lo selecciona el abogado.
    tecnico_encargado_id = Column(Integer, nullable=False)
    # Fecha del concepto (= fecha de firma).
    fecha_aceptacion = Column(Date)
    caudal_fuente = Column(Float)
    caudal_disponible = Column(Float)
    caudal_otorgado = Column(Float)
    num_usuarios = Column(Integer)
    cumple = Column(Boolean)
    # El DBML lo pide NOT NULL, pero la fila nace al seleccionar el técnico
    # (antes de que exista el concepto firmado, plan §4-E): se llena al cargar
    # la versión final.
    doc_concepto_tecnico_id = Column(Integer)

    expediente = relationship("Expediente", back_populates="concepto_tecnico")

    __table_args__ = (
        Index('ix_concepto_tecnico_tecnico', 'tecnico_encargado_id'),
    )
