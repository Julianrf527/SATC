import logging
import traceback

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

from db.database import SessionLocal
from db.models.permiso import Permiso
from db.models.rol import Rol
from db.models.rol_permiso import RolPermiso
from db.models.usuario import Usuario

load_dotenv()

logger = logging.getLogger(__name__)

PERMISOS = [
    {"nombre": "admin_roles_y_permisos", "menu_path": "/user/role"},
    {"nombre": "admin_registrar_usuarios", "menu_path": "/user/add"},
    {"nombre": "admin_gestionar_usuarios", "menu_path": "/user/manage"},
    {"nombre": "sancionatorio_gestionar", "menu_path": "/file/manage"},
    {"nombre": "sancionatorio_consultar", "menu_path": "/file/consult"},
    {"nombre": "sancionatorio_alertas", "menu_path": "/file/alerts"},
    {"nombre": "sancionatorio_asignar", "menu_path": "/file/assign_manage"},
    {"nombre": "involucrado_gestionar", "menu_path": "/involved/manage"},
    {"nombre": "documento_gestionar", "menu_path": "/document/manage"},
    {"nombre": "documento_crear", "menu_path": ""},
    {"nombre": "documento_revisar", "menu_path": ""},
    {"nombre": "auditoria_usuarios", "menu_path": "/audit/users"},
    {"nombre": "auditoria_expedientes", "menu_path": "/audit/files"},
    {"nombre": "auditoria_involucrados", "menu_path": "/audit/involved"},
    {"nombre": "auditoria_infracciones", "menu_path": "/audit/infractions"},
    {"nombre": "infraccion_gestionar", "menu_path": "/infraction/manage"},
    {"nombre": "infraccion_consultar", "menu_path": "/infraction/consult"},
    {"nombre": "infraccion_alertas", "menu_path": "/infraction/alerts"},
    {"nombre": "infraccion_asignar", "menu_path": "/infraction/assign_manage"},
    {"nombre": "infraccion_asignar_informes", "menu_path": "/infraction/reports"},
    {"nombre": "subir_informes", "menu_path": ""},
]


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


async def _seed_admin_user(session: AsyncSession) -> None:
    """Crea usuario administrador inicial."""
    admin_data = {
        "numero_documento": 1233506795,
        "primer_nombre": "Julian",
        "segundo_nombre": None,
        "primer_apellido": "Rodriguez",
        "segundo_apellido": None,
        "correo": "julianrf527@gmail.com",
        "hash_contrasena": "$2b$12$zRj0wuQfYsr7VWDjT6A34.qPh6PtrhlQv9zH1dReZRamRwmGXKXGW",
        "activo": True,
        "rol_id": 1,
    }
    usuario = Usuario(**admin_data)
    session.add(usuario)
    await session.flush()
    logger.info("Admin user created: %s %s", admin_data["primer_nombre"], admin_data["primer_apellido"])


async def seed_initial_data() -> None:
    """
    Seeds initial database data: permissions, admin role, and admin user.
    Uses database lock to prevent concurrent execution across workers.
    """
    async with SessionLocal() as session:
        try:
            lock_acquired = await _acquire_seed_lock(session)
            if not lock_acquired:
                logger.info("Another worker is seeding, skipping")
                return

            result = await session.execute(select(Permiso).limit(1))
            if result.scalars().first():
                logger.info("Initial data already exists, skipping")
                return

            logger.info("Starting seed operation")

            permisos = await _seed_permissions(session)
            await _seed_admin_role(session, permisos)
            await _seed_admin_user(session)

            await session.commit()
            logger.info("Seed operation completed successfully")

        except Exception as e:
            await session.rollback()
            logger.exception("Seed operation failed: %s", e)
            raise

