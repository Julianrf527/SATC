from sqlalchemy import Column, Integer, String, TIMESTAMP, Index, Text
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class FileHash(Base):
    """
    Tabla para almacenar hashes de archivos y evitar duplicados en MinIO.
    Cuando se sube un archivo, se calcula su hash SHA256 y se busca en esta tabla.
    Si existe, se reutiliza la URL del archivo existente.
    """
    __tablename__ = "file_hash"

    id = Column(Integer, autoincrement=True, primary_key=True)
    file_hash = Column(String(64), unique=True, nullable=False, index=True)  # SHA256 tiene 64 caracteres hex
    file_url = Column(Text, nullable=False)  # URL del archivo en MinIO (bucket/path)
    original_filename = Column(String(255))  # Nombre original del primer archivo con este hash
    content_type = Column(String(100))  # MIME type del archivo
    file_size = Column(Integer)  # Tamaño en bytes
    reference_count = Column(Integer, default=1)  # Contador de cuántas veces se referencia este archivo
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota")),
        nullable=False
    )
    last_referenced_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota")),
        nullable=False
    )

    # Índices para optimizar búsquedas
    __table_args__ = (
        Index('ix_file_hash_hash', 'file_hash'),
    )
