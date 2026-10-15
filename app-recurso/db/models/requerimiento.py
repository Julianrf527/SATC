from sqlalchemy import Column, Integer, String, ForeignKey, Date, Index
from sqlalchemy.orm import relationship
from .base import Base, VersionadoMixin

class Requerimiento(VersionadoMixin, Base):
    """``expediente_id`` solo cuando es la etapa 3; como sub-proceso de
    memorias/obras queda NULL y lo referencia el padre."""
    __tablename__ = 'requerimiento'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), unique=True)
    # app-users. Abogado que se asignó ("Asignarme para diligenciar"). NULL solo en
    # cargue histórico de super gestión sin encargado (desviación del DBML).
    encargado_acto_id = Column(Integer)
    # Se llena al numerar el acto.
    acto_admin_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"), unique=True)
    radicado_oficio_entrada = Column(String(15))
    fecha_oficio_entrada = Column(Date)
    doc_oficio_entrada_id = Column(Integer)
    concepto_tecnico_id = Column(Integer, ForeignKey('concepto_tecnico.id', onupdate="CASCADE"), unique=True)

    expediente = relationship("Expediente", back_populates="requerimiento")
    acto_administrativo = relationship("ActoAdministrativo")
    concepto_tecnico = relationship("ConceptoTecnico")

    __table_args__ = (
        Index('ix_requerimiento_encargado', 'encargado_acto_id'),
    )
