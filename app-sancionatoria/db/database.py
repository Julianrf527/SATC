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
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: models.Base.metadata.create_all(sync_conn, checkfirst=True))
