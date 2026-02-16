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

# Si necesitas crear tablas automáticamente
async def init_db():
    from models import base  # Asegúrate de que models.Base exista
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
