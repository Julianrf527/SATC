from sqlalchemy import Column, Integer, String
from .base import Base

class Permiso(Base):
    __tablename__ = "permiso"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    nombre      = Column(String(40), nullable=False, unique=True)
    menu_path   = Column(String(50))
    # Texto corto para la pantalla de roles ("Desbloquea X. Sirve para Y.").
    # En bases existentes la agrega db/permission_sync.py (ADD COLUMN IF NOT EXISTS).
    # Obligatoria: "Desbloquea X. Sirve para Y." Se define al crear/editar el
    # permiso; la sincronización del catálogo solo llena las que falten.
    descripcion = Column(String(200), nullable=False)
