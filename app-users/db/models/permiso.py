from sqlalchemy import Column, Integer, String
from .base import Base

class Permiso(Base):
    __tablename__ = "permiso"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    nombre    = Column(String(40), nullable=False, unique=True)
    menu_path = Column(String(50))
