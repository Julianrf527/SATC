from sqlalchemy import Column, Integer, String, TIMESTAMP, Index
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class DocumentoAnexo(Base):
    __tablename__ = 'documento_anexo'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Referencia polimórfica: etapa_tipo identifica la tabla de etapa, etapa_ref_id su ID
    # Valores válidos de etapa_tipo: 'indagacion', 'apertura_probatoria',
    # 'cierre_probatoria', 'decision_fondo'
    etapa_tipo = Column(String(50), nullable=False)
    etapa_ref_id = Column(Integer, nullable=False)
    nombre = Column(String(100), nullable=False)
    documento_anexo_id = Column(Integer, nullable=False)  # ref → app-docs
    fecha_subida = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    __table_args__ = (
        # _get_anexos (stage.py) filtra por este par en cada GET de etapa.
        Index("ix_documento_anexo_etapa", "etapa_tipo", "etapa_ref_id"),
    )
