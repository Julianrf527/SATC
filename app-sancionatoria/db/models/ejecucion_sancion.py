from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base

class EjecucionSancion(Base):
    __tablename__ = 'ejecucion_sancion'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_acto = Column(String(15))
    acto_administrativo_numerado = Column(Integer)
    fecha_auto = Column(Date)
    documento_acto_id = Column(Integer)
    cobro_coactivo = Column(Boolean)
    documento_cobro_id = Column(Integer)
    disposicion = Column(Boolean)
    ruia = Column(Boolean)
    documento_ruia_id = Column(Integer)
    memorando = Column(Boolean)
    documento_memorando_id = Column(Integer)
    etapa_id = Column(Integer, ForeignKey('etapa.id'), unique=True)

    etapa = relationship("Etapa", back_populates="ejecucion_sancion")
