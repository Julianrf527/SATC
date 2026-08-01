from sqlalchemy import Column, Integer, Date, TIMESTAMP, Index, String
from sqlalchemy.orm import relationship
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class ActoAdministrativo(Base):
    __tablename__ = 'acto_administrativo'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tipo_acto = Column(String(15))
    numerado = Column(Integer)
    fecha_numerado = Column(Date)
    fecha_asigncion_juridica = Column(Date)
    documento_acto_administrativo_id = Column(Integer)
    fecha_creacion = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    etapa_acoger_concepto = relationship("EtapaAcogerConcepto", back_populates="acto_administrativo")
    etapa_cierre = relationship("EtapaCierre", back_populates="acto_administrativo")
    medida_preventiva = relationship("MedidaPreventiva", back_populates="acto_administrativo", uselist=False)
    notificaciones = relationship("Notificacion", back_populates="acto_administrativo", cascade="all, delete-orphan")
    comunicacion = relationship("Comunicacion", back_populates="acto_admin", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_acto_admin_fecha_creacion', 'fecha_creacion'),
    )
