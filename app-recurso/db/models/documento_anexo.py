from sqlalchemy import Column, Integer, String, TIMESTAMP, Index
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class DocumentoAnexo(Base):
    __tablename__ = 'documentos_anexos'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Referencia polimórfica (nombre de la tabla de la etapa + id): no admite FK real.
    etapa_tipo = Column(String(50), nullable=False)
    etapa_ref_id = Column(Integer, nullable=False)
    nombre = Column(String(100), nullable=False)
    documento_anexo_id = Column(Integer, nullable=False)
    fecha_subida = Column(TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    __table_args__ = (
        Index('ix_documentos_anexos_etapa', 'etapa_tipo', 'etapa_ref_id'),
    )
