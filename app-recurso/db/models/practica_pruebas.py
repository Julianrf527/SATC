from sqlalchemy import Column, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base, VersionadoMixin


class PracticaPruebas(VersionadoMixin, Base):
    """Práctica de pruebas del recurso de reposición (cuando ``requiere_pruebas``).

    Lleva el «Auto que admite y decreta práctica de pruebas» (acto que solo se
    comunica) y, al cargar su versión final, nace el concepto técnico de la
    práctica (``concepto_tecnico_id``). Con ese concepto cargado se habilita el
    acto que resuelve el recurso."""
    __tablename__ = 'practica_pruebas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    recurso_id = Column(Integer, ForeignKey('recurso_reposicion.id', onupdate="CASCADE", ondelete="CASCADE"),
                        unique=True, nullable=False)
    # id en app-users (otra BD): FK lógica, sin constraint. Cualquier abogado se asigna.
    encargado_acto_id = Column(Integer)
    acto_admin_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="RESTRICT"), unique=True)
    concepto_tecnico_id = Column(Integer, ForeignKey('concepto_tecnico.id', onupdate="CASCADE"), unique=True)

    recurso = relationship("RecursoReposicion", back_populates="practica_pruebas")
    acto_administrativo = relationship("ActoAdministrativo")
    concepto_tecnico = relationship("ConceptoTecnico")

    __table_args__ = (
        Index('ix_practica_pruebas_encargado', 'encargado_acto_id'),
    )
