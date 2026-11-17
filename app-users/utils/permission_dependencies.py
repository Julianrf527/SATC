"""
Consultas sobre dependencias obligatorias (tabla permiso_requiere) e
incompatibilidades (tabla permiso_excluye) entre permisos.

Funcionan tanto con AsyncSession (rutas) como con AsyncConnection (sincronización
al arrancar), porque solo usan `execute(select(...))`.
"""
from sqlalchemy import select
from sqlalchemy.orm import aliased

from db.models.permiso import Permiso
from db.models.permiso_excluye import PermisoExcluye
from db.models.permiso_requiere import PermisoRequiere
from db.permission_catalog import EXENTO_INCOMPATIBLES
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


async def excluidos_por_permiso(permiso_ids: list[int], db) -> dict[int, list[str]]:
    """{permiso_id: [nombres de los permisos con los que no puede ir]} para los ids dados."""
    if not permiso_ids:
        return {}
    excluido = aliased(Permiso, name="excluido")
    stmt = (
        select(PermisoExcluye.permiso_id, excluido.nombre)
        .join(excluido, excluido.id == PermisoExcluye.excluye_id)
        .where(PermisoExcluye.permiso_id.in_(permiso_ids))
        .order_by(PermisoExcluye.permiso_id, excluido.nombre)
    )
    resultado: dict[int, list[str]] = {}
    for permiso_id, nombre in (await db.execute(stmt)).all():
        resultado.setdefault(permiso_id, []).append(nombre)
    return resultado


async def incompatibles_presentes(permiso_ids: list[int], db) -> list[tuple[str, str]]:
    """Pares (a, b), con a < b, de permisos incompatibles que tendría un rol con
    exactamente `permiso_ids`. Vacío si el rol administra roles (exento)."""
    ids = list(set(permiso_ids))
    if not ids:
        return []
    nombres = set((await db.execute(select(Permiso.nombre).where(Permiso.id.in_(ids)))).scalars().all())
    if EXENTO_INCOMPATIBLES in nombres:
        return []
    uno, otro = aliased(Permiso, name="uno"), aliased(Permiso, name="otro")
    stmt = (
        select(uno.nombre, otro.nombre)
        .select_from(PermisoExcluye)
        .join(uno, uno.id == PermisoExcluye.permiso_id)
        .join(otro, otro.id == PermisoExcluye.excluye_id)
        .where(PermisoExcluye.permiso_id.in_(ids), PermisoExcluye.excluye_id.in_(ids), uno.nombre < otro.nombre)
        .order_by(uno.nombre, otro.nombre)
    )
    return [(a, b) for a, b in (await db.execute(stmt)).all()]


def mensaje_incompatibles(pares: list[tuple[str, str]]) -> str:
    """Mensaje en español para el 422."""
    partes = [f"«{a}» no puede ir con «{b}»" for a, b in pares]
    return "El rol tiene permisos incompatibles: " + "; ".join(partes) + "."


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
    """Roles que hoy tienen un permiso sin todos sus requeridos o dos permisos
    incompatibles (salvo los que administran roles), con lo que incumplen.

    [{"rol_id", "rol_nombre", "faltantes": [{"permiso", "requiere": [..]}],
      "incompatibles": [{"permiso", "con"}]}]
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

    def fila(rol_id, rol_nombre):
        return roles.setdefault(rol_id, {"rol_id": rol_id, "rol_nombre": rol_nombre, "faltantes": {}, "incompatibles": []})

    for rol_id, rol_nombre, permiso, requerido in (await db.execute(stmt)).all():
        fila(rol_id, rol_nombre)["faltantes"].setdefault(permiso, []).append(requerido)

    # Incompatibilidades: el rol tiene los dos permisos y no administra roles.
    rp_a, rp_b, rp_ex = aliased(RolPermiso, name="rp_a"), aliased(RolPermiso, name="rp_b"), aliased(RolPermiso, name="rp_ex")
    uno, otro, exento = aliased(Permiso, name="uno"), aliased(Permiso, name="otro"), aliased(Permiso, name="exento")
    administra = (
        select(rp_ex.permiso_id)
        .join(exento, exento.id == rp_ex.permiso_id)
        .where(rp_ex.rol_id == rp_a.rol_id, exento.nombre == EXENTO_INCOMPATIBLES)
        .correlate(rp_a)
        .exists()
    )
    stmt_inc = (
        select(Rol.id, Rol.nombre, uno.nombre, otro.nombre)
        .select_from(rp_a)
        .join(PermisoExcluye, PermisoExcluye.permiso_id == rp_a.permiso_id)
        .join(rp_b, (rp_b.rol_id == rp_a.rol_id) & (rp_b.permiso_id == PermisoExcluye.excluye_id))
        .join(Rol, Rol.id == rp_a.rol_id)
        .join(uno, uno.id == PermisoExcluye.permiso_id)
        .join(otro, otro.id == PermisoExcluye.excluye_id)
        .where(uno.nombre < otro.nombre, ~administra)
        .order_by(Rol.id, uno.nombre, otro.nombre)
    )
    for rol_id, rol_nombre, a, b in (await db.execute(stmt_inc)).all():
        fila(rol_id, rol_nombre)["incompatibles"].append({"permiso": a, "con": b})

    return [
        {
            "rol_id": r["rol_id"],
            "rol_nombre": r["rol_nombre"],
            "faltantes": [{"permiso": p, "requiere": req} for p, req in r["faltantes"].items()],
            "incompatibles": r["incompatibles"],
        }
        for r in sorted(roles.values(), key=lambda r: r["rol_id"])
    ]
