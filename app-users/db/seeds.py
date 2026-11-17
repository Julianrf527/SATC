import logging
import os
import traceback

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from db.database import SessionLocal
from db.models.permiso import Permiso
from db.models.rol import Rol
from db.models.rol_permiso import RolPermiso
from db.models.usuario import Usuario
from db.permission_catalog import PERMISOS
from utils.passwords import hash_password

load_dotenv()

logger = logging.getLogger(__name__)

# Catálogo único (nombre, menu_path, descripcion): db/permission_catalog.py.
# Los cambios posteriores en bases ya sembradas los aplica db/permission_sync.py.

# Usuario administrador inicial: sus datos vienen de variables de entorno
# (archivo .env.user_admin, ver .env.user_admin.example), nunca del código.
ADMIN_OBLIGATORIAS = ("ADMIN_NUMERO_DOCUMENTO", "ADMIN_PRIMER_NOMBRE", "ADMIN_PRIMER_APELLIDO", "ADMIN_CORREO")
# Contraseña en texto plano (se hashea aquí) o un hash bcrypt ya calculado.
ADMIN_CLAVES = ("ADMIN_PASSWORD", "ADMIN_HASH_CONTRASENA")
# Serializa la creación del admin entre workers (no depende de seed_lock).
_LOCK_ADMIN = 815123004


async def _acquire_seed_lock(session: AsyncSession) -> bool:
    """Intenta adquirir lock de base de datos para evitar concurrencia."""
    try:
        await session.execute(text("""
            CREATE TABLE IF NOT EXISTS seed_lock (
                id INTEGER PRIMARY KEY DEFAULT 1,
                locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CHECK (id = 1)
            )
        """))
        await session.commit()

        result = await session.execute(text("""
            INSERT INTO seed_lock (id) VALUES (1)
            ON CONFLICT (id) DO NOTHING
            RETURNING id
        """))
        return result.fetchone() is not None
    except Exception as e:
        logger.warning("Lock fallback: %s", e)
        return True


async def _seed_permissions(session: AsyncSession) -> list:
    """Inserta permisos iniciales."""
    permisos = []
    for perm_data in PERMISOS:
        permiso = Permiso(**perm_data)
        session.add(permiso)
        permisos.append(permiso)
    await session.flush()
    logger.info("Inserted %d permissions", len(PERMISOS))
    return permisos


async def _seed_admin_role(session: AsyncSession, permisos: list) -> None:
    """Crea rol admin y vincula permisos."""
    rol_admin = Rol(id=1, nombre="admin")
    session.add(rol_admin)
    await session.flush()
    logger.info("Admin role created")

    for permiso in permisos:
        session.add(RolPermiso(rol_id=1, permiso_id=permiso.id))
    await session.flush()
    logger.info("Linked %d permissions to admin role", len(permisos))


def admin_desde_entorno(env=os.environ) -> dict | None:
    """Datos del admin inicial desde el entorno, o None si no están completos.

    Sin ninguna variable ADMIN_* no se crea admin (aviso en el log). Si están
    a medias se indica cuáles faltan. La contraseña se toma de ADMIN_PASSWORD
    (se hashea) o de ADMIN_HASH_CONTRASENA (hash bcrypt ya calculado).
    """
    valor = lambda k: (env.get(k) or "").strip()  # noqa: E731
    if not any(valor(k) for k in ADMIN_OBLIGATORIAS + ADMIN_CLAVES):
        logger.warning("Sin variables ADMIN_* (.env.user_admin): no se crea el usuario administrador")
        return None
    faltan = [k for k in ADMIN_OBLIGATORIAS if not valor(k)]
    if not any(valor(k) for k in ADMIN_CLAVES):
        faltan.append(" o ".join(ADMIN_CLAVES))
    if faltan:
        logger.error("Usuario administrador no creado: faltan %s en .env.user_admin", ", ".join(faltan))
        return None
    try:
        documento = int(valor("ADMIN_NUMERO_DOCUMENTO"))
    except ValueError:
        logger.error("Usuario administrador no creado: ADMIN_NUMERO_DOCUMENTO debe ser numérico")
        return None
    return {
        "numero_documento": documento,
        "primer_nombre": valor("ADMIN_PRIMER_NOMBRE"),
        "segundo_nombre": valor("ADMIN_SEGUNDO_NOMBRE") or None,
        "primer_apellido": valor("ADMIN_PRIMER_APELLIDO"),
        "segundo_apellido": valor("ADMIN_SEGUNDO_APELLIDO") or None,
        "correo": valor("ADMIN_CORREO"),
        "hash_contrasena": valor("ADMIN_HASH_CONTRASENA") or hash_password(valor("ADMIN_PASSWORD")),
    }


async def _seed_admin_user(session: AsyncSession) -> None:
    """Crea el administrador inicial si la base aún no tiene usuarios.

    Corre en cada arranque (no solo en la primera siembra), así un admin que
    falte se crea en cuanto se completa .env.user_admin.
    """
    await session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _LOCK_ADMIN})
    if (await session.execute(select(Usuario.id).limit(1))).first() is not None:
        return
    rol_admin = (await session.execute(select(Rol).where(Rol.nombre == "admin"))).scalars().first()
    if rol_admin is None:
        logger.warning("Sin rol admin: no se crea el usuario administrador")
        return
    datos = admin_desde_entorno()
    if datos is None:
        return
    session.add(Usuario(**datos, activo=True, rol_id=rol_admin.id))
    await session.flush()
    logger.info("Usuario administrador inicial creado (documento %s)", datos["numero_documento"])


async def seed_initial_data() -> None:
    """
    Seeds initial database data: permissions, admin role, and admin user.
    Permisos y rol solo en la primera siembra (seed_lock evita que dos workers
    lo hagan a la vez); el usuario administrador se revisa en cada arranque.
    """
    async with SessionLocal() as session:
        try:
            if not await _acquire_seed_lock(session):
                logger.info("Permissions already seeded (or another worker is seeding)")
            elif (await session.execute(select(Permiso).limit(1))).scalars().first():
                logger.info("Initial data already exists, skipping")
            else:
                logger.info("Starting seed operation")
                permisos = await _seed_permissions(session)
                await _seed_admin_role(session, permisos)
                await session.commit()
                logger.info("Seed operation completed successfully")

            await _seed_admin_user(session)
            await session.commit()

        except Exception as e:
            await session.rollback()
            logger.exception("Seed operation failed: %s", e)
            raise

