from sqlalchemy import Column, Integer, String, ForeignKey, Date
from sqlalchemy.orm import relationship
from .base import Base

class Subsanacion(Base):
    __tablename__ = 'subsanacion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    radicado = Column(String(15), unique=True, nullable=False)
    fecha_radicado = Column(Date, nullable=False)
    doc_planos_ajustados_id = Column(Integer, nullable=False)
    concepto_tecnico_id = Column(Integer, ForeignKey('concepto_tecnico.id', onupdate="CASCADE"), unique=True)

    concepto_tecnico = relationship("ConceptoTecnico")
