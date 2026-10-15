import logging

from fastapi import Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import SessionLocal

logger = logging.getLogger(__name__)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def get_db_managed(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        yield db
    except (HTTPException, RequestValidationError):
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en {request.method} {request.url.path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
