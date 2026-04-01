from sqlalchemy import Column, Integer, String
from .base import Base

class Rol(Base):
    __tablename__ = "rol"

    id     = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(20), nullable=False)
