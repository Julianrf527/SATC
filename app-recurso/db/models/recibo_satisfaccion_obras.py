from sqlalchemy import Column, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, VersionadoMixin

class ReciboSatisfaccionObras(VersionadoMixin, Base):
    __tablename__ = 'recibo_satisfaccion_obras'

    id = Column(Integer, primary_key=True, autoincrement=True)
    expediente_id = Column(Integer, ForeignKey('expediente.id', onupdate="CASCADE", ondelete="CASCADE"), unique=True, nullable=False)
    informe_usuario_id = Column(Integer, ForeignKey('informe_usuario.id', onupdate="CASCADE"), unique=True, nullable=False)
    concepto_tecnico_id = Column(Integer, ForeignKey('concepto_tecnico.id', onupdate="CASCADE"), unique=True)
    requerimiento_id = Column(Integer, ForeignKey('requerimiento.id', onupdate="CASCADE"), unique=True)
    nuevo_informe_usuario_id = Column(Integer, ForeignKey('informe_usuario.id', onupdate="CASCADE"), unique=True)
    concepto_tecnico_segundo_id = Column(Integer, ForeignKey('concepto_tecnico.id', onupdate="CASCADE"), unique=True)
    # id en app-users (otra BD): FK lógica, sin constraint.
    encargado_acto_id = Column(Integer)
    acto_admin_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"), unique=True)

    expediente = relationship("Expediente", back_populates="recibo_satisfaccion_obras")
    # Dos FK a informe_usuario y dos a concepto_tecnico: foreign_keys desambigua.
    informe_usuario = relationship("InformeUsuario", foreign_keys=[informe_usuario_id])
    nuevo_informe_usuario = relationship("InformeUsuario", foreign_keys=[nuevo_informe_usuario_id])
    concepto_tecnico = relationship("ConceptoTecnico", foreign_keys=[concepto_tecnico_id])
    concepto_tecnico_segundo = relationship("ConceptoTecnico", foreign_keys=[concepto_tecnico_segundo_id])
    requerimiento = relationship("Requerimiento")
    acto_administrativo = relationship("ActoAdministrativo")

    __table_args__ = (
        Index('ix_recibo_obras_encargado', 'encargado_acto_id'),
    )
