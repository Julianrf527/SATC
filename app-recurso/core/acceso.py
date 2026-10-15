"""Autenticación y permisos comunes a todas las rutas (plan §2 y §6-V1).

Uso en una ruta::

    usuario = await requiere_permiso(request, Permission.MANAGE)
    usuario.user_id, usuario.super_gestion

``requiere_permiso`` acepta varios permisos (basta uno). ``super_gestion``
indica si además tiene ``recurso_super_gestion``: ese usuario omite las
validaciones de negocio (§2.1), nunca las restricciones de la BD.
"""
from dataclasses import dataclass

from fastapi import HTTPException, Request

from core.permission import Permission
from services.users import verify_permission
from utils.verify_token import verify_gateway_token


@dataclass(frozen=True)
class Usuario:
    user_id: int
    rol_id: int
    super_gestion: bool = False


async def usuario_actual(request: Request) -> Usuario:
    token = verify_gateway_token(request)
    return Usuario(user_id=token["user_id"], rol_id=token["rol_id"])


async def tiene_permiso(user_id: int, *permisos: str) -> bool:
    for permiso in permisos:
        if await verify_permission(user_id, permiso):
            return True
    return False


async def requiere_permiso(request: Request, *permisos: str) -> Usuario:
    """403 si el usuario no tiene ninguno de ``permisos``."""
    usuario = await usuario_actual(request)
    if permisos and not await tiene_permiso(usuario.user_id, *permisos):
        raise HTTPException(status_code=403, detail="No tienes permiso para esta acción")
    super_gestion = await verify_permission(usuario.user_id, Permission.SUPER_MANAGE)
    return Usuario(usuario.user_id, usuario.rol_id, super_gestion)


async def requiere_lectura(request: Request) -> Usuario:
    """Consultar: basta consultar, gestionar o super gestión."""
    return await requiere_permiso(request, Permission.CONSULT, Permission.MANAGE, Permission.SUPER_MANAGE)


async def requiere_gestion(request: Request) -> Usuario:
    """Escritura (V1): gestionar o super gestión."""
    return await requiere_permiso(request, Permission.MANAGE, Permission.SUPER_MANAGE)
