"""
Sincronización idempotente del catálogo de permisos (db/permission_catalog.py)
con la base de datos. Corre en cada arranque de app-users, después del seed.

Por qué existe: el seed (db/seeds.py) solo siembra una base vacía, así que cada
permiso nuevo, descripción o renombre exigía SQL manual en la VM. Esta rutina
lo hace sola y se puede correr N veces con el mismo resultado:

1. Esquema: `ADD COLUMN IF NOT EXISTS descripcion` y `CREATE TABLE IF NOT EXISTS
   permiso_requiere` (create_all no altera tablas existentes).
2. Renombres (RENOMBRES): si existe el nombre viejo y no el nuevo, se renombra
   la fila (conserva id, y con él los roles que lo tenían). Si existen ambos no
   se borra nada: queda una advertencia en el log para resolverlo a mano.
3. Upsert por nombre: inserta los permisos del catálogo que falten; llena
   `descripcion` y `menu_path` SOLO si hoy están vacíos/NULL, para no pisar
   lo editado desde la pantalla de permisos (la descripción es obligatoria y
   la define quien crea o edita el permiso).
   Nunca borra permisos que no estén en el catálogo.
4. Permisos recién insertados se otorgan a los roles "superadministrador"
   (los que ya tenían TODOS los permisos existentes). Sin esto nadie podría
   verlos ni asignarlos: la pantalla de roles solo lista y deja otorgar
   permisos que el propio rol tiene. Es la única escritura sobre roles y solo
   ocurre la vez en que el permiso nace; no aplica a permisos ya existentes.
5. permiso_requiere = DEPENDENCIAS (agrega las que falten, quita las que sobren).
6. Reporta en el log los roles que incumplen dependencias. No los modifica.

Concurrencia: varios workers de Gunicorn arrancan a la vez; todo va en una sola
transacción tomada con pg_advisory_xact_lock, así que corren en serie y el
segundo encuentra todo hecho.
"""
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from db.permission_catalog import DEPENDENCIAS, PERMISOS, RENOMBRES
from utils.permission_dependencies import roles_que_incumplen

logger = logging.getLogger(__name__)

# Distinto del lock de init_db (815123002).
PERMISSION_SYNC_LOCK = 815123003

_DDL_ESQUEMA = (
    "ALTER TABLE permiso ADD COLUMN IF NOT EXISTS descripcion VARCHAR(200)",
    """
    CREATE TABLE IF NOT EXISTS permiso_requiere (
        permiso_id  INTEGER NOT NULL REFERENCES permiso(id) ON DELETE CASCADE ON UPDATE CASCADE,
        requiere_id INTEGER NOT NULL REFERENCES permiso(id) ON DELETE CASCADE ON UPDATE CASCADE,
        PRIMARY KEY (permiso_id, requiere_id)
    )
    """,
)


async def asegurar_esquema_permisos(conn: AsyncConnection) -> None:
    """DDL idempotente que create_all no hace sobre tablas ya existentes."""
    for ddl in _DDL_ESQUEMA:
        await conn.execute(text(ddl))


async def _renombrar(conn: AsyncConnection, resumen: dict) -> None:
    for viejo, nuevo in RENOMBRES:
        rows = (await conn.execute(
            text("SELECT nombre FROM permiso WHERE nombre IN (:viejo, :nuevo)"),
            {"viejo": viejo, "nuevo": nuevo},
        )).scalars().all()
        if viejo in rows and nuevo in rows:
            logger.warning(
                "[permisos] Existen '%s' y '%s' a la vez: no se renombra ni se borra nada. "
                "Revise a mano qué roles tienen el viejo y elimínelo.", viejo, nuevo,
            )
            resumen["advertencias"].append(f"duplicado:{viejo}->{nuevo}")
        elif viejo in rows:
            await conn.execute(
                text("UPDATE permiso SET nombre = :nuevo WHERE nombre = :viejo"),
                {"viejo": viejo, "nuevo": nuevo},
            )
            logger.info("[permisos] Renombrado '%s' -> '%s'", viejo, nuevo)
            resumen["renombrados"].append((viejo, nuevo))


async def _roles_superadmin(conn: AsyncConnection) -> list[int]:
    """Roles que tienen todos los permisos existentes (antes de insertar nuevos)."""
    total = (await conn.execute(text("SELECT COUNT(*) FROM permiso"))).scalar_one()
    if not total:
        return []
    return list((await conn.execute(
        text(
            "SELECT rol_id FROM rol_permiso GROUP BY rol_id "
            "HAVING COUNT(DISTINCT permiso_id) = :total ORDER BY rol_id"
        ),
        {"total": total},
    )).scalars().all())


async def _upsert_permisos(conn: AsyncConnection, resumen: dict) -> list[int]:
    filas = (await conn.execute(
        text("SELECT id, nombre, menu_path, descripcion FROM permiso")
    )).mappings().all()
    existentes = {f["nombre"]: f for f in filas}
    insertados: list[int] = []

    for p in PERMISOS:
        actual = existentes.get(p["nombre"])
        if actual is None:
            nuevo_id = (await conn.execute(
                text(
                    "INSERT INTO permiso (nombre, menu_path, descripcion) "
                    "VALUES (:nombre, :menu_path, :descripcion) RETURNING id"
                ),
                p,
            )).scalar_one()
            insertados.append(nuevo_id)
            resumen["insertados"].append(p["nombre"])
            continue

        cambios = {}
        if not (actual["descripcion"] or "").strip() and p["descripcion"]:
            cambios["descripcion"] = p["descripcion"]
        if not actual["menu_path"] and p["menu_path"]:
            cambios["menu_path"] = p["menu_path"]
        if cambios:
            sets = ", ".join(f"{col} = :{col}" for col in cambios)
            await conn.execute(
                text(f"UPDATE permiso SET {sets} WHERE id = :id"),
                {**cambios, "id": actual["id"]},
            )
            resumen["actualizados"].append(p["nombre"])

    return insertados


async def _sincronizar_dependencias(conn: AsyncConnection, resumen: dict) -> None:
    ids = {
        nombre: pid for pid, nombre in
        (await conn.execute(text("SELECT id, nombre FROM permiso"))).all()
    }
    deseadas = set()
    for permiso, requeridos in DEPENDENCIAS.items():
        for requerido in requeridos:
            if permiso in ids and requerido in ids:
                deseadas.add((ids[permiso], ids[requerido]))
    actuales = {
        (a, b) for a, b in
        (await conn.execute(text("SELECT permiso_id, requiere_id FROM permiso_requiere"))).all()
    }
    for permiso_id, requiere_id in sorted(deseadas - actuales):
        await conn.execute(
            text("INSERT INTO permiso_requiere (permiso_id, requiere_id) VALUES (:p, :r)"),
            {"p": permiso_id, "r": requiere_id},
        )
    for permiso_id, requiere_id in sorted(actuales - deseadas):
        await conn.execute(
            text("DELETE FROM permiso_requiere WHERE permiso_id = :p AND requiere_id = :r"),
            {"p": permiso_id, "r": requiere_id},
        )
    resumen["dependencias_agregadas"] = len(deseadas - actuales)
    resumen["dependencias_quitadas"] = len(actuales - deseadas)


async def _descripcion_obligatoria(conn: AsyncConnection, resumen: dict) -> None:
    """La descripción es obligatoria. Los permisos fuera del catálogo que aún no
    tengan (creados antes de existir la columna) reciben un texto provisional
    para poder aplicar NOT NULL; se corrige desde la pantalla de permisos."""
    sin = (await conn.execute(text(
        "SELECT id, nombre FROM permiso WHERE descripcion IS NULL OR btrim(descripcion) = ''"
    ))).all()
    for pid, nombre in sin:
        await conn.execute(
            text("UPDATE permiso SET descripcion = :d WHERE id = :id"),
            {"d": f"Permiso {nombre}. Falta su descripción: edítela en Roles y permisos.", "id": pid},
        )
        resumen["advertencias"].append(f"'{nombre}' sin descripción: se puso un texto provisional")
    # Idempotente: no falla si ya es NOT NULL.
    await conn.execute(text("ALTER TABLE permiso ALTER COLUMN descripcion SET NOT NULL"))


async def sincronizar_permisos(conn: AsyncConnection) -> dict:
    """Aplica el catálogo sobre `conn`. El llamador maneja la transacción (begin/commit)."""
    resumen = {
        "renombrados": [],
        "insertados": [],
        "actualizados": [],
        "otorgados_a_roles": [],
        "dependencias_agregadas": 0,
        "dependencias_quitadas": 0,
        "roles_incumplen": [],
        "advertencias": [],
    }
    await conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": PERMISSION_SYNC_LOCK})
    await asegurar_esquema_permisos(conn)
    await _renombrar(conn, resumen)

    superadmins = await _roles_superadmin(conn)
    insertados = await _upsert_permisos(conn, resumen)
    if insertados:
        if superadmins:
            for rol_id in superadmins:
                for permiso_id in insertados:
                    await conn.execute(
                        text(
                            "INSERT INTO rol_permiso (rol_id, permiso_id) VALUES (:r, :p) "
                            "ON CONFLICT DO NOTHING"
                        ),
                        {"r": rol_id, "p": permiso_id},
                    )
            resumen["otorgados_a_roles"] = superadmins
            logger.info(
                "[permisos] %d permiso(s) nuevo(s) otorgado(s) a los roles con todos los permisos: %s",
                len(insertados), superadmins,
            )
        else:
            logger.warning(
                "[permisos] Permisos nuevos %s sin rol que los administre: ningún rol tenía "
                "todos los permisos. Asígnelos a un rol administrador.", resumen["insertados"],
            )

    await _sincronizar_dependencias(conn, resumen)
    await _descripcion_obligatoria(conn, resumen)

    resumen["roles_incumplen"] = await roles_que_incumplen(conn)
    for rol in resumen["roles_incumplen"]:
        detalle = "; ".join(
            f"{f['permiso']} requiere {', '.join(f['requiere'])}" for f in rol["faltantes"]
        )
        logger.warning(
            "[permisos] El rol %s ('%s') incumple dependencias (no se modifica): %s",
            rol["rol_id"], rol["rol_nombre"], detalle,
        )

    logger.info(
        "[permisos] Sincronización: renombrados=%s insertados=%s actualizados=%d "
        "dependencias +%d/-%d, roles que incumplen=%d",
        resumen["renombrados"], resumen["insertados"], len(resumen["actualizados"]),
        resumen["dependencias_agregadas"], resumen["dependencias_quitadas"],
        len(resumen["roles_incumplen"]),
    )
    return resumen


async def sync_permission_catalog() -> dict:
    """Punto de entrada del startup: una transacción propia sobre el engine de la app."""
    from db.database import engine

    async with engine.begin() as conn:
        return await sincronizar_permisos(conn)
