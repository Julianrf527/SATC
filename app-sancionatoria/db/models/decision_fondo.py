from sqlalchemy import Column, Integer, Text, ForeignKey
from .base import Base

class DecisionFondo(Base):
    __tablename__ = "decision_fondo"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_sancion_id = Column(Integer, ForeignKey("tipo_decision.id", ondelete="SET NULL", onupdate="CASCADE"))
    detalle = Column(Text)
    etapa_id = Column(Integer, ForeignKey("etapa.id", ondelete="SET NULL", onupdate="CASCADE"))
