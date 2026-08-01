from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

#----- DB -----

from db.models.permiso import Permiso
from db.models.rol_permiso import RolPermiso
from db.models.usuario import Usuario
from db.models.rol import Rol

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def get_role_permissions(rol_id: int, db: AsyncSession) -> set[int]:
    """IDs de los permisos que tiene un rol."""
    stmt = (
        select(RolPermiso.permiso_id)
        .where(RolPermiso.rol_id == rol_id)
    )
    
    result = await db.execute(stmt)
    permission_ids = result.scalars().all()
    
    return set(permission_ids)

async def get_user_permission_names(permissions_ids: list[int], db: AsyncSession) -> set[str]:
    """Nombres de los permisos correspondientes a una lista de IDs."""
    stmt = (
        select(Permiso.nombre)
        .where(Permiso.id.in_(permissions_ids))
    )

    result = await db.execute(stmt)
    permission_names = result.scalars().all()

    return set(permission_names)

async def get_permissions_by_rol_id(rol_id: int, db: AsyncSession) -> list:
    """Permisos de un rol leídos de la BD.

    Se consulta siempre la BD y no el token: un permiso creado después de
    emitirse el token no aparecería en él.
    """
    stmt = (
        select(Permiso.id, Permiso.nombre, Permiso.menu_path)
        .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
        .where(RolPermiso.rol_id == rol_id)
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [
        {
            "id": row.id,
            "nombre": row.nombre,
            "name": row.nombre,
            "menu_path": row.menu_path,
        }
        for row in rows
    ]

async def get_user_permission_avaliable(permissions_user: set[str], db: AsyncSession) -> list:
    stmt = select(Permiso.id, Permiso.nombre, Permiso.menu_path).where(Permiso.nombre.in_(permissions_user))
    permission = await db.execute(stmt)
    permission = permission.all()
    return [
        {
            "id": row.id,
            "nombre": row.nombre,
            "name": row.nombre,
            "menu_path": row.menu_path,
        }
        for row in permission
    ]

async def get_user_rol_avaliable(permissions_user: set[str], db: AsyncSession) -> list:
    stmt = (
        select(
            Rol.id.label("rol_id"),
            Rol.nombre.label("rol_nombre"),
            Permiso.id.label("permiso_id"),
            Permiso.nombre.label("permiso_nombre"),
        )
        .outerjoin(RolPermiso, RolPermiso.rol_id == Rol.id)
        .outerjoin(Permiso, Permiso.id == RolPermiso.permiso_id)
    )

    result = await db.execute(stmt)
    rows = result.all()
    roles = {}

    for row in rows:
        if row.rol_id not in roles:
            roles[row.rol_id] = {
                "id": row.rol_id,
                "name": row.rol_nombre,
                "permission_ids": set(),
                "permission_names": set()
            }
        if row.permiso_nombre is not None:
            roles[row.rol_id]["permission_ids"].add(row.permiso_id)
            roles[row.rol_id]["permission_names"].add(row.permiso_nombre)

    permissions_user_set = set(permissions_user)
    role_avaliable = [
        {
            "id": r["id"],
            "nombre": r["name"],
            "permission": list(r["permission_ids"]),
            "permisos": list(r["permission_ids"]),
        }
        for r in roles.values()
        if r["permission_names"].issubset(permissions_user_set)
    ]

    return role_avaliable