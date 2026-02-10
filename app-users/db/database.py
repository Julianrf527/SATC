# database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import os


load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

engine = create_async_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    from models import base  
    async with engine.begin() as conn:
        await conn.run_sync(base.metadata.create_all)
