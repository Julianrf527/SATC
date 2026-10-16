import logging

from fastapi import Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import SessionLocal
from services.usos_archivos import registro_peticion

logger = logging.getLogger(__name__)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def get_db_managed(request: Request, db: AsyncSession = Depends(get_db)):
    """Sesión de las rutas de escritura. Si la operación termina en error, el
    uso de archivos sumado en app-docs y no confirmado por un commit se
    compensa (``services.usos_archivos``) antes de propagar el error original."""
    try:
        async with registro_peticion(db, f"({request.method} {request.url.path})"):
            yield db
    except (HTTPException, RequestValidationError):
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en {request.method} {request.url.path}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error interno del servidor")
