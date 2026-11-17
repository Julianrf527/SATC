from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

engine = create_async_engine(
    DATABASE_URL,
    connect_args={
        "server_settings": {"client_encoding": "utf8"}
    },
    pool_pre_ping=True
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
        # Tablas nuevas (BD vacía). No altera tablas existentes: eso lo hace
        # aplicar_migraciones (DDL idempotente + recreación de la vista, que
        # create_all no crea).
        await conn.run_sync(models.Base.metadata.create_all)
        await aplicar_migraciones(conn)

    print("Esquema de documentos_db y vista vista_documentos_detalle actualizados")
