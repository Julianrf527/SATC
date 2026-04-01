from sqlalchemy import Column, Integer, Text
from sqlalchemy.orm import relationship
from .base import Base

class TipoSancion(Base):
    __tablename__ = 'tipo_sancion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(Text)

    decisiones = relationship("DecisionFondo", back_populates="tipo_sancion")
