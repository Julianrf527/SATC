"""Autenticación y permisos comunes a todas las rutas (plan §2 y §6-V1).

Uso en una ruta::

    usuario = await requiere_permiso(request, Permission.MANAGE)
    usuario.user_id, usuario.super_gestion

``requiere_permiso`` acepta varios permisos (basta uno). ``super_gestion``
indica si además tiene ``recurso_super_gestion``: ese usuario omite las
validaciones de negocio (§2.1), nunca las restricciones de la BD.
"""
import asyncio
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


async def _consultar(user_id: int, permisos: tuple[str, ...]) -> dict[str, bool]:
    """Consulta los permisos en paralelo (cacheados por ``services.users``)."""
    unicos = tuple(dict.fromkeys(permisos))
    resultados = await asyncio.gather(*(verify_permission(user_id, p) for p in unicos))
    return dict(zip(unicos, resultados))


async def tiene_permiso(user_id: int, *permisos: str) -> bool:
    return any((await _consultar(user_id, permisos)).values())


async def requiere_permiso(request: Request, *permisos: str) -> Usuario:
    """403 si el usuario no tiene ninguno de ``permisos``."""
    usuario = await usuario_actual(request)
    tiene = await _consultar(usuario.user_id, (*permisos, Permission.SUPER_MANAGE))
    if permisos and not any(tiene[p] for p in permisos):
        raise HTTPException(status_code=403, detail="No tienes permiso para esta acción")
    return Usuario(usuario.user_id, usuario.rol_id, tiene[Permission.SUPER_MANAGE])


async def requiere_lectura(request: Request) -> Usuario:
    """Consultar: basta consultar, gestionar o super gestión."""
    return await requiere_permiso(request, Permission.CONSULT, Permission.MANAGE, Permission.SUPER_MANAGE)


async def requiere_gestion(request: Request) -> Usuario:
    """Escritura (V1): gestionar o super gestión."""
    return await requiere_permiso(request, Permission.MANAGE, Permission.SUPER_MANAGE)
