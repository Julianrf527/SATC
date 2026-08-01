# database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import asyncio
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os


load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

# Dimensionado para ~50 usuarios simultáneos.
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


async def init_db(max_retries: int = 8, base_delay: float = 1.5):
    from . import models

    async def _sync_sequences(conn):
        # Las secuencias SERIAL quedan atrás si se sembró con IDs explícitos:
        # sin este setval el siguiente insert choca con una PK ya usada.
        await conn.execute(text(
            """
            SELECT setval(
                pg_get_serial_sequence('rol', 'id'),
                COALESCE((SELECT MAX(id) FROM rol), 1),
                (SELECT MAX(id) FROM rol) IS NOT NULL
            )
            """
        ))
        await conn.execute(text(
            """
            SELECT setval(
                pg_get_serial_sequence('permiso', 'id'),
                COALESCE((SELECT MAX(id) FROM permiso), 1),
                (SELECT MAX(id) FROM permiso) IS NOT NULL
            )
            """
        ))
        await conn.execute(text(
            """
            SELECT setval(
                pg_get_serial_sequence('usuario', 'id'),
                COALESCE((SELECT MAX(id) FROM usuario), 1),
                (SELECT MAX(id) FROM usuario) IS NOT NULL
            )
            """
        ))

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT pg_advisory_lock(815123002)"))
                try:
                    await conn.run_sync(models.Base.metadata.create_all, checkfirst=True)
                    await _sync_sequences(conn)
                finally:
                    await conn.execute(text("SELECT pg_advisory_unlock(815123002)"))
            return
        except OperationalError:
            if attempt == max_retries:
                raise
            await asyncio.sleep(base_delay * attempt)
