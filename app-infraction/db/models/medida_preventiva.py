from sqlalchemy import Column, Integer, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class MedidaPreventiva(Base):
    __tablename__ = 'medida_preventiva'

    id = Column(Integer, primary_key=True, autoincrement=True)
    etapa_respuesta_id = Column(Integer, ForeignKey('etapa_respuesta.id', onupdate="CASCADE", ondelete="CASCADE"), unique=True)
    tipo_medida_id = Column(Integer, ForeignKey('tipo_medida.id'))
    cantidad = Column(Text)
    especie = Column(Text)
    estado_medida = Column(Boolean)
    acto_administrativo_id = Column(Integer, ForeignKey('acto_administrativo.id', onupdate="CASCADE", ondelete="SET NULL"), nullable=True)

    etapa_respuesta = relationship("EtapaRespuesta", back_populates="medida_preventiva")
    tipo_medida = relationship("TipoMedida", back_populates="medidas")
    acto_administrativo = relationship("ActoAdministrativo", back_populates="medida_preventiva")
