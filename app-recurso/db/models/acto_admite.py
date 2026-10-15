from sqlalchemy import Column, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, VersionadoMixin

class ActoAdmite(VersionadoMixin, Base):
    __tablename__ = 'acto_admite'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), unique=True, nullable=False)
    # app-users. Abogado que se asignó ("Asignarme para diligenciar"). NULL solo en
    # cargue histórico de super gestión sin encargado (desviación del DBML).
    encargado_acto_id = Column(Integer)
    # Se llena al numerar el acto.
    acto_admin_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"), unique=True)
    doc_oficio_alcaldia_id = Column(Integer)
    doc_fijacion_aviso_id = Column(Integer)
    doc_constancia_fijacion_aviso_id = Column(Integer)

    expediente = relationship("Expediente", back_populates="acto_admite")
    acto_administrativo = relationship("ActoAdministrativo")

    __table_args__ = (
        Index('ix_acto_admite_encargado', 'encargado_acto_id'),
    )
