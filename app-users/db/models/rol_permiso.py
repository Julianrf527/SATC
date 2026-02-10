from sqlalchemy import Column, Integer, ForeignKey
from .base import Base

class RolPermiso(Base):
    __tablename__ = "rol_permiso"

    rol_id = Column(Integer, ForeignKey("rol.id", ondelete="SET NULL", onupdate="CASCADE"), primary_key=True)
    permiso_id = Column(Integer, ForeignKey("permiso.id", ondelete="SET NULL", onupdate="CASCADE"), primary_key=True)
