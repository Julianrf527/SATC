from sqlalchemy import Column, Integer, Text, ForeignKey, String
from sqlalchemy.orm import relationship
from .base import Base

class InvolucradoExpediente(Base):
    __tablename__ = "involucrado_expediente"
    
    involucrado_id = Column(Integer, ForeignKey("involucrado.id", ondelete="SET NULL", onupdate="CASCADE"), primary_key=True)
    expediente_radicado = Column(
        String, 
        ForeignKey("expediente.radicado", ondelete="SET NULL", onupdate="CASCADE"), 
        primary_key=True
    )
    
    expediente = relationship("Expediente", back_populates="involucrados")