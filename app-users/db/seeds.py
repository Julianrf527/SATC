from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import SessionLocal
from db.models.permiso import Permiso
from db.models.rol import Rol
from db.models.rol_permiso import RolPermiso
from db.models.usuario import Usuario
from dotenv import load_dotenv
import os

load_dotenv()


# Datos iniciales de permisos (mejorados pero mantienen compatibilidad con slider)
PERMISOS = [
    # === ADMINISTRACIÓN (prefix: admin_) ===
    {"nombre": "admin_roles", "menu_path": "/user/role"},
    {"nombre": "admin_crear_usuarios", "menu_path": "/user/add"},
    {"nombre": "admin_gestionar_usuarios", "menu_path": "/user/manage"},

    # === EXPEDIENTES (prefix: expediente_) ===
    {"nombre": "expediente_gestionar", "menu_path": "/file/manage"},
    {"nombre": "expediente_consultar", "menu_path": "/file/consult"},
    {"nombre": "expediente_alertas", "menu_path": "/file/alerts"},
    {"nombre": "expediente_asignar", "menu_path": "/file/assign_manage"},

    # === INVOLUCRADOS (prefix: involucrado_) ===
    {"nombre": "involucrado_gestionar", "menu_path": "/involved/manage"},

    # === DOCUMENTOS (prefix: documento_) ===
    {"nombre": "documento_gestionar", "menu_path": "/document/manage"},
    {"nombre": "documento_crear", "menu_path": ""},
    {"nombre": "documento_revisar", "menu_path": ""},

    # === AUDITORÍA (prefix: auditoria_) ===
    {"nombre": "auditoria_usuarios", "menu_path": "/audit/users"},
    {"nombre": "auditoria_expedientes", "menu_path": "/audit/files"},
    {"nombre": "auditoria_involucrados", "menu_path": "/audit/involved"},
    # === INFRACCIONES (prefix: infraccion_) ===
    {"nombre": "infraccion_gestionar", "menu_path": "/infraction/manage"},
]

# Rol admin con todos los permisos (1-15)
PERMISOS_ROL_ADMIN = list(range(1, 16))


async def seed_initial_data():
    """
    Ejecuta el seedeo de datos iniciales.
    - Siempre crea: permisos y rol admin
    - Crear usuario admin Julian Rodriguez (indispensable)
    - Usa un lock para evitar concurrencia entre workers

    """
    async with SessionLocal() as session:
        try:
            # Lock basado en BD para evitar concurrencia entre workers
            # Intentar crear una tabla temporal como semáforo
            await session.execute("""
                CREATE TABLE IF NOT EXISTS seed_lock (
                    id INTEGER PRIMARY KEY DEFAULT 1,
                    locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CHECK (id = 1)
                )
            """)
            await session.commit()

            # Intentar tomar el lock
            result = await session.execute("""
                INSERT INTO seed_lock (id) VALUES (1)
                ON CONFLICT (id) DO NOTHING
                RETURNING id
            """)
            lock_acquired = result.fetchone() is not None

            if not lock_acquired:
                print("Otro worker ya está ejecutando el seedeo, skipping...")
                return

            print("Lock adquirido - ejecutando seedeo...")

        except Exception as lock_error:
            # Si hay error en el lock, continúa con verificación normal
            print(f"Warning: Error en lock, usando verificación normal: {lock_error}")

        # Verificar si ya existen permisos
        result = await session.execute(select(Permiso).limit(1))
        if result.scalars().first():
            print("Datos iniciales ya existen en user_db, skipping seedeo")
            return

        print("Iniciando seedeo de user_db...")

        try:
            # 1. Insertar permisos
            for perm_data in PERMISOS:
                permiso = Permiso(**perm_data)
                session.add(permiso)
            await session.flush()
            print(f"✓ Insertados {len(PERMISOS)} permisos")

            # 2. Crear rol admin
            rol_admin = Rol(id=1, nombre="admin")
            session.add(rol_admin)
            await session.flush()
            print("✓ Creado rol 'admin'")

            # 3. Vincular permisos al rol admin
            for permiso_id in PERMISOS_ROL_ADMIN:
                rol_permiso = RolPermiso(rol_id=1, permiso_id=permiso_id)
                session.add(rol_permiso)
            await session.flush()
            print(f"✓ Vinculados {len(PERMISOS_ROL_ADMIN)} permisos al rol admin")

            # 4. Crear usuario admin (Julian Rodriguez - indispensable)
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
            print(f"✓ Creado usuario admin: {admin_data['primer_nombre']} {admin_data['primer_apellido']}")

            # Commit
            await session.commit()
            print("✓ Seedeo completado exitosamente\n")

        except Exception as e:
            import traceback
            await session.rollback()
            print(f"✗ Error durante seedeo: {e}")
            print(f"✗ Stacktrace completo: {traceback.format_exc()}")
            raise

