"""
Consultas sobre dependencias obligatorias entre permisos (tabla permiso_requiere).

Funcionan tanto con AsyncSession (rutas) como con AsyncConnection (sincronización
al arrancar), porque solo usan `execute(select(...))`.
"""
from sqlalchemy import select
from sqlalchemy.orm import aliased

from db.models.permiso import Permiso
from db.models.permiso_requiere import PermisoRequiere
from db.models.rol import Rol
from db.models.rol_permiso import RolPermiso

_Dependiente = aliased(Permiso, name="dependiente")
_Requerido = aliased(Permiso, name="requerido")


async def requeridos_por_permiso(permiso_ids: list[int], db) -> dict[int, list[str]]:
    """{permiso_id: [nombres de los permisos que exige]} para los ids dados."""
    if not permiso_ids:
        return {}
    stmt = (
        select(PermisoRequiere.permiso_id, _Requerido.nombre)
        .join(_Requerido, _Requerido.id == PermisoRequiere.requiere_id)
        .where(PermisoRequiere.permiso_id.in_(permiso_ids))
        .order_by(PermisoRequiere.permiso_id, _Requerido.nombre)
    )
    resultado: dict[int, list[str]] = {}
    for permiso_id, requerido in (await db.execute(stmt)).all():
        resultado.setdefault(permiso_id, []).append(requerido)
    return resultado


async def dependencias_faltantes(permiso_ids: list[int], db) -> list[tuple[str, str]]:
    """Pares (permiso, requerido) que faltan si un rol tuviera exactamente `permiso_ids`.

    Basta con revisar las dependencias directas: si A exige B y B exige C, un rol
    con A debe tener B, y al tener B se le exige C. Así las cadenas quedan
    cubiertas sin calcular el cierre transitivo.
    """
    ids = list(set(permiso_ids))
    if not ids:
        return []
    stmt = (
        select(_Dependiente.nombre, _Requerido.nombre)
        .select_from(PermisoRequiere)
        .join(_Dependiente, _Dependiente.id == PermisoRequiere.permiso_id)
        .join(_Requerido, _Requerido.id == PermisoRequiere.requiere_id)
        .where(
            PermisoRequiere.permiso_id.in_(ids),
            PermisoRequiere.requiere_id.notin_(ids),
        )
        .order_by(_Dependiente.nombre, _Requerido.nombre)
    )
    return [(p, r) for p, r in (await db.execute(stmt)).all()]


def mensaje_dependencias_faltantes(faltantes: list[tuple[str, str]]) -> str:
    """Mensaje en español para el 422: agrupa por permiso dependiente."""
    agrupado: dict[str, list[str]] = {}
    for permiso, requerido in faltantes:
        agrupado.setdefault(permiso, []).append(requerido)
    partes = [
        f"«{permiso}» requiere " + " y ".join(f"«{r}»" for r in requeridos)
        for permiso, requeridos in agrupado.items()
    ]
    return "El rol no cumple las dependencias de permisos: " + "; ".join(partes) + "."


async def roles_que_incumplen(db) -> list[dict]:
    """Roles que hoy tienen un permiso sin todos sus requeridos, con lo que les falta.

    [{"rol_id", "rol_nombre", "faltantes": [{"permiso", "requiere": [..]}]}]
    """
    otro = aliased(RolPermiso, name="otro")
    tiene_requerido = (
        select(otro.permiso_id)
        .where(
            otro.rol_id == RolPermiso.rol_id,
            otro.permiso_id == PermisoRequiere.requiere_id,
        )
        .correlate(RolPermiso, PermisoRequiere)
        .exists()
    )
    stmt = (
        select(Rol.id, Rol.nombre, _Dependiente.nombre, _Requerido.nombre)
        .select_from(RolPermiso)
        .join(Rol, Rol.id == RolPermiso.rol_id)
        .join(PermisoRequiere, PermisoRequiere.permiso_id == RolPermiso.permiso_id)
        .join(_Dependiente, _Dependiente.id == PermisoRequiere.permiso_id)
        .join(_Requerido, _Requerido.id == PermisoRequiere.requiere_id)
        .where(~tiene_requerido)
        .order_by(Rol.id, _Dependiente.nombre, _Requerido.nombre)
    )
    roles: dict[int, dict] = {}
    for rol_id, rol_nombre, permiso, requerido in (await db.execute(stmt)).all():
        rol = roles.setdefault(rol_id, {"rol_id": rol_id, "rol_nombre": rol_nombre, "faltantes": {}})
        rol["faltantes"].setdefault(permiso, []).append(requerido)
    return [
        {
            "rol_id": r["rol_id"],
            "rol_nombre": r["rol_nombre"],
            "faltantes": [{"permiso": p, "requiere": req} for p, req in r["faltantes"].items()],
        }
        for r in roles.values()
    ]
