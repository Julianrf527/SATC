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

engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=30,
    echo_pool=False,
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
    from .migrations import aplicar_migraciones

    async with engine.begin() as conn:
        await conn.execute(text("SELECT pg_advisory_lock(815123003)"))
        try:
            # Crea tablas y tipos ENUM nuevos. No altera tablas existentes:
            # eso lo hace aplicar_migraciones con DDL idempotente.
            await conn.run_sync(models.Base.metadata.create_all, checkfirst=True)
            await aplicar_migraciones(conn)
        finally:
            await conn.execute(text("SELECT pg_advisory_unlock(815123003)"))
