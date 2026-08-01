"""Endpoints service-to-service (X-Service-Token): consulta de usuarios por otros microservicios."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List
import logging

#----- DB -----
from db.deps import get_db_managed
from db.models.usuario import Usuario
from db.models.rol_permiso import RolPermiso
from db.models.permiso import Permiso

router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

#----------- FUNCIONES ----------
from utils.verify_token import verify_service_token


class UserBatchRequest(BaseModel):
    user_ids: List[int]


def _nombre_completo(u) -> str:
    partes = [u.primer_nombre]
    if u.segundo_nombre:
        partes.append(u.segundo_nombre)
    partes.append(u.primer_apellido)
    if u.segundo_apellido:
        partes.append(u.segundo_apellido)
    return " ".join(partes)


@router.post("/batch")
async def obtener_usuarios_batch(
    request: Request,
    data: UserBatchRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Obtiene información básica de múltiples usuarios por sus IDs.
    SOLO para comunicación entre servicios internos.
    """
    verify_service_token(request)

    if not data.user_ids:
        return JSONResponse(content={"ok": True, "data": []}, status_code=200)

    if len(data.user_ids) > 100:
        raise HTTPException(status_code=400, detail="Máximo 100 usuarios por solicitud")

    stmt = select(
        Usuario.id,
        Usuario.numero_documento,
        Usuario.primer_nombre,
        Usuario.segundo_nombre,
        Usuario.primer_apellido,
        Usuario.segundo_apellido,
        Usuario.correo
    ).where(Usuario.id.in_(data.user_ids))

    result = await db.execute(stmt)
    users = result.fetchall()

    users_data = [
        {
            "id": user.id,
            "numero_documento": user.numero_documento,
            "nombre": _nombre_completo(user),
            "correo": user.correo
        }
        for user in users
    ]

    return JSONResponse(content={"ok": True, "data": users_data}, status_code=200)


@router.get("/permission/{permission_name}")
async def obtener_usuarios_por_permiso(
    request: Request,
    permission_name: str,
    db: AsyncSession = Depends(get_db_managed)
):
    """
    Obtiene información básica de múltiples usuarios por permiso.
    SOLO para comunicación entre servicios internos.
    """
    verify_service_token(request)

    permiso_id = (
        await db.execute(select(Permiso.id).where(Permiso.nombre == permission_name))
    ).scalar_one_or_none()

    if not permiso_id:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")

    result = await db.execute(
        select(
            Usuario.id,
            Usuario.numero_documento,
            Usuario.primer_nombre,
            Usuario.segundo_nombre,
            Usuario.primer_apellido,
            Usuario.segundo_apellido,
            Usuario.correo
        )
        .select_from(Usuario)
        .join(RolPermiso, Usuario.rol_id == RolPermiso.rol_id)
        .where(RolPermiso.permiso_id == permiso_id)
    )

    rows = result.fetchall()

    users_data = [
        {
            "id": r.id,
            "numero_documento": r.numero_documento,
            "nombre": _nombre_completo(r),
            "correo": r.correo
        }
        for r in rows
    ]

    return JSONResponse(content={"ok": True, "data": users_data}, status_code=200)
