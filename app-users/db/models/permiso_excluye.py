from sqlalchemy import Column, Integer, ForeignKey
from .base import Base


class PermisoExcluye(Base):
    """Incompatibilidad: un rol con `permiso_id` no puede tener `excluye_id`.

    Se guarda en los dos sentidos (A excluye B y B excluye A). La llena
    db/permission_sync.py desde db/permission_catalog.py (INCOMPATIBLES) en cada
    arranque. No aplica a los roles que administran roles (ver
    EXENTO_INCOMPATIBLES en el catálogo).
    """
    __tablename__ = "permiso_excluye"

    permiso_id = Column(Integer, ForeignKey("permiso.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
    excluye_id = Column(Integer, ForeignKey("permiso.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
