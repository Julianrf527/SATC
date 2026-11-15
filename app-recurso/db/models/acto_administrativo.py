from sqlalchemy import CheckConstraint, Column, Integer, Date, String, TIMESTAMP, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class ActoAdministrativo(Base):
    __tablename__ = 'acto_administrativo'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # COMUNICA o NOTIFICA (``MedioActo``), según la etapa que lo expide
    # (``services.actos.MEDIO_POR_ETAPA``). Qué acto es lo dice esa etapa.
    medio = Column(String(10), nullable=False)
    # Forma del acto: Auto o Resolución. La elige quien carga o corrige el acto;
    # cada una lleva su propia numeración. NULL solo en filas anteriores a la
    # columna (ver db/migrations.py); la API la exige.
    clase_acto = Column(String(4))
    numerado = Column(Integer, nullable=False)
    fecha_numerado = Column(Date, nullable=False)
    documento_acto_administrativo_id = Column(Integer, nullable=False)
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    comunicacion = relationship("Comunicacion", back_populates="acto_administrativo", uselist=False, cascade="all, delete-orphan")
    notificaciones = relationship("Notificacion", back_populates="acto_administrativo", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_acto_admin_clase_numerado', 'clase_acto', 'numerado'),
        Index('ix_acto_admin_fecha_numerado', 'fecha_numerado'),
        CheckConstraint("clase_acto IN ('AUTO', 'RES')", name='ck_acto_admin_clase_acto'),
        CheckConstraint("medio IN ('COMUNICA', 'NOTIFICA')", name='ck_acto_admin_medio'),
    )
