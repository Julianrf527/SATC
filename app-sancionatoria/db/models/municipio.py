from sqlalchemy import Column, Integer, String
from .base import Base

class Municipio(Base):
    __tablename__ = "municipio"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(20))
