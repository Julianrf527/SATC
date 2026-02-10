from sqlalchemy import Column, Integer, String
from .base import Base

class Rol(Base):
    __tablename__ = "rol"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(50), nullable=False, unique=True)
