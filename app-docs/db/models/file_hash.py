from sqlalchemy import Column, Integer, String, TIMESTAMP, Text
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class FileHash(Base):
    __tablename__ = "file_hash"

    id = Column(Integer, autoincrement=True, primary_key=True)
    # unique=True ya crea el índice de búsqueda por hash (deduplicación).
    file_hash = Column(String(64), unique=True, nullable=False)
    file_url = Column(Text, nullable=False)
    content_type = Column(String(100))
    file_size = Column(Integer)
    numero_usos = Column(Integer, default=0, nullable=False) # Contador de usos del hash
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota")),
        nullable=False
    )
    # Última vez que alguien subió estos bytes (nuevo o deduplicado). La
    # limpieza solo borra archivos sin uso cuya última subida supera el periodo
    # de gracia: así no borra uno recién subido que el módulo aún no asocia.
    ultima_subida = Column(TIMESTAMP(timezone=True), nullable=True)
