# database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os


load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

# Optimización para alta concurrencia (50+ usuarios simultáneos)
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,          # 10 conexiones base (5 por worker)
    max_overflow=30,       # Hasta 40 conexiones totales para picos de 50+ users
    pool_pre_ping=True,    # Verificar conexiones antes de usar
    pool_recycle=3600,     # Reciclar conexiones cada hora
    pool_timeout=30,       # Timeout esperando conexión disponible
    echo_pool=False,       # Logging de connection pool (disable en prod)
    connect_args={
        "server_settings": {"client_encoding": "utf8"}
    }
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    from . import models
    async with engine.begin() as conn:
        await conn.execute(text("SELECT pg_advisory_lock(815123001)"))
        try:
            await conn.run_sync(models.Base.metadata.create_all, checkfirst=True)
        finally:
            await conn.execute(text("SELECT pg_advisory_unlock(815123001)"))
