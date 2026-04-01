from sqlalchemy import Column, Integer, String, TIMESTAMP, Index, Text
from datetime import datetime
from zoneinfo import ZoneInfo
from .base import Base

class FileHash(Base):
    __tablename__ = "file_hash"

    id = Column(Integer, autoincrement=True, primary_key=True)
    file_hash = Column(String(64), unique=True, nullable=False, index=True)
    file_url = Column(Text, nullable=False)
    content_type = Column(String(100))
    file_size = Column(Integer)
    numero_usos = Column(Integer, default=0, nullable=False) # Contador de usos del hash
    created_at = Column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(ZoneInfo("America/Bogota")),
        nullable=False
    )

    __table_args__ = (
        Index('ix_file_hash_hash', 'file_hash'),
    )
