from sqlalchemy import Column, Integer, String, ForeignKey
from .base import Base

class Vereda(Base):
    __tablename__ = "vereda"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(25))
    municipio_id = Column(Integer, ForeignKey("municipio.id", ondelete="SET NULL", onupdate="CASCADE"))
