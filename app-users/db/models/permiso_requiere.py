from sqlalchemy import Column, Integer, ForeignKey
from .base import Base


class PermisoRequiere(Base):
    """Dependencia obligatoria: un rol con `permiso_id` debe tener `requiere_id`.

    Un solo sentido. La llena db/permission_sync.py desde
    db/permission_catalog.py (DEPENDENCIAS) en cada arranque.
    """
    __tablename__ = "permiso_requiere"

    permiso_id  = Column(Integer, ForeignKey("permiso.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    requiere_id = Column(Integer, ForeignKey("permiso.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
