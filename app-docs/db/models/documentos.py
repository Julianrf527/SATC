from sqlalchemy import Column, Integer, String, Text, TIMESTAMP
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import relationship
from .base import Base

class Documento(Base):
    __tablename__ = "documentos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255))
    descripcion = Column(Text)
    tipo_archivo = Column(String(10))
    # Se filtra por creador en /list y /stats
    usuario_creador_id = Column(Integer, index=True)
    # Se ordena por fecha en /list
    fecha_creacion = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota")),
        index=True
    )
    # Se filtra por estado en /list y /stats
    estado = Column(String(20), index=True)
    version_actual = Column(Integer)
    numero_devoluciones = Column(Integer, default=0)
    fecha_ultima_actualizacion = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )

    versiones = relationship("VersionDocumento", back_populates="documento", lazy="select")
    revisiones = relationship("Revision", back_populates="documento", lazy="select")
    asignaciones_revisores = relationship("AsignacionRevisor", back_populates="documento", lazy="select")
    auditoria = relationship("AuditoriaDocumento", back_populates="documento", lazy="select")
