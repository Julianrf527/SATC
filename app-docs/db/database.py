from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

# URL de conexión a la base de datos (ejemplo con PostgreSQL)
# Puedes cambiarla por la que uses: MySQL, SQLite, etc.
load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

# Crear el motor asíncrono con configuración UTF-8 para PostgreSQL
engine = create_async_engine(
    DATABASE_URL,
    connect_args={
        "server_settings": {"client_encoding": "utf8"}
    },
    pool_pre_ping=True
)

# Crear la sesión local
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Crear tablas y vista al iniciar
async def init_db():
    from . import models
    from sqlalchemy import text

    async with engine.begin() as conn:
        # 1. Crear tablas desde los modelos ORM
        await conn.run_sync(models.Base.metadata.create_all)

        # 2. Crear la vista vista_documentos_detalle (las vistas no las crea create_all)
        await conn.execute(text("""
            CREATE OR REPLACE VIEW vista_documentos_detalle AS
            SELECT
                d.id,
                d.id AS documento_id,
                d.nombre,
                d.descripcion,
                d.tipo_archivo,
                d.estado,
                d.version_actual,
                d.numero_devoluciones,
                d.usuario_creador_id,
                d.fecha_creacion,
                d.fecha_ultima_actualizacion,
                COALESCE(rev_count.total_revisiones, 0) AS total_revisiones,
                COALESCE(asig_count.total_revisores, 0) AS total_revisores
            FROM documentos d
            LEFT JOIN (
                SELECT documento_id, COUNT(*) AS total_revisiones
                FROM revisiones
                GROUP BY documento_id
            ) rev_count ON rev_count.documento_id = d.id
            LEFT JOIN (
                SELECT documento_id, COUNT(*) AS total_revisores
                FROM asignaciones_revisores
                GROUP BY documento_id
            ) asig_count ON asig_count.documento_id = d.id
        """))

    print("Vista vista_documentos_detalle creada/actualizada correctamente")
