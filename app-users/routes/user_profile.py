"""Autogestión del perfil del usuario autenticado: contraseña y datos propios."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, EmailStr, validator
import logging

#----- DB -----
from db.deps import get_db_managed
from db.models.usuario import Usuario

router = APIRouter()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

#----------- FUNCIONES ----------
from utils.passwords import hash_password, verify_password_async
from utils.redis_session import get_redis_client
from utils.verify_token import verify_gateway_token
from utils.insertLog import insert_auditoria

# ---------- MODELOS ----------

class CambiarContrasenaRequest(BaseModel):
    current_password: str
    new_password: str

class UsuarioRequest(BaseModel):
    first_name: str
    middle_name: str = ""
    lastname: str
    second_lastname: str = ""
    correo: EmailStr

    @validator('first_name', 'middle_name', 'lastname', 'second_lastname')
    def validate_names(cls, v):
        """Valida y limpia los nombres"""
        if v:
            v = v.strip()
            if len(v) > 20:
                raise ValueError('El nombre no puede exceder 20 caracteres')
            if not all(c.isalpha() or c.isspace() for c in v):
                raise ValueError('El nombre solo puede contener letras')
        return v

    @validator('correo')
    def validate_email_lowercase(cls, v):
        """Convierte el email a minúsculas"""
        return v.lower() if v else v

# ---------- ENDPOINTS ----------

@router.post("/password-change")
async def cambiar_contrasena(
    request: Request,
    data: CambiarContrasenaRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)

    stmt = select(Usuario).where(Usuario.id == token_data["user_id"])
    result = await db.execute(stmt)
    usuario = result.scalar_one_or_none()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not await verify_password_async(data.current_password, usuario.hash_contrasena):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")

    new_password_hashed = hash_password(data.new_password)
    await db.execute(update(Usuario).where(Usuario.id == usuario.id).values(hash_contrasena=new_password_hashed))

    # Cambiar la contraseña cierra la sesión activa en todos los dispositivos.
    r = get_redis_client()

    if r:
        await r.delete(f"session:user:{token_data['user_id']}")
    else:
        logger.warning("Redis no disponible, no se pudo eliminar sesión tras cambio de contraseña")

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
        tipo_evento="CAMBIO_CONTRASENA",
        resultado="EXITOSO",
        detalle=f"Cambio de contraseña del usuario {token_data['user_id']}",
        datos_nuevos={"accion": "cambio_contrasena"}
    )

    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error al guardar registro de auditoría"
        )

    await db.commit()

    return JSONResponse(content={"ok": True, "message": "Contraseña actualizada"}, status_code=200)

@router.put("/update-user")
async def update_user(
    request: Request,
    data: UsuarioRequest,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)

    def capitalize_name(name: str) -> str:
        return name.strip().capitalize() if name else ""

    first_name = capitalize_name(data.first_name)
    middle_name = capitalize_name(data.middle_name) if data.middle_name else ""
    lastname = capitalize_name(data.lastname)
    second_lastname = capitalize_name(data.second_lastname) if data.second_lastname else ""
    nuevo_correo = data.correo.lower()

    full_name_parts = [first_name]
    if middle_name:
        full_name_parts.append(middle_name)
    full_name_parts.append(lastname)
    if second_lastname:
        full_name_parts.append(second_lastname)
    full_name = " ".join(full_name_parts)

    usuario = await db.scalar(
        select(Usuario).where(Usuario.id == token_data["user_id"])
    )
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    datos_anteriores = {
        "numero_documento": usuario.numero_documento,
        "primer_nombre": usuario.primer_nombre,
        "segundo_nombre": usuario.segundo_nombre,
        "primer_apellido": usuario.primer_apellido,
        "segundo_apellido": usuario.segundo_apellido,
        "correo": usuario.correo
    }

    existe_correo = await db.scalar(
        select(Usuario).where(
            Usuario.correo == nuevo_correo,
            Usuario.id != token_data["user_id"]
        )
    )
    if existe_correo:
        raise HTTPException(
            status_code=400,
            detail="El correo ya está en uso por otro usuario"
        )

    stmt = (
        update(Usuario)
        .where(Usuario.id == token_data["user_id"])
        .values(
            primer_nombre=first_name,
            segundo_nombre=middle_name if middle_name else None,
            primer_apellido=lastname,
            segundo_apellido=second_lastname if second_lastname else None,
            correo=nuevo_correo
        )
    )
    await db.execute(stmt)

    datos_nuevos = {
        "numero_documento": usuario.numero_documento,
        "nombre_completo": full_name,
        "primer_nombre": first_name,
        "segundo_nombre": middle_name if middle_name else None,
        "primer_apellido": lastname,
        "segundo_apellido": second_lastname if second_lastname else None,
        "correo": nuevo_correo
    }

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
        tipo_evento="ACTUALIZACION_PERFIL",
        resultado="EXITOSO",
        detalle=f"Actualización de datos del usuario {full_name}",
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos
    )

    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error al guardar registro de auditoría"
        )

    await db.commit()

    return JSONResponse(
        content={
            "ok": True,
            "message": "Datos actualizados correctamente",
            "data": {
                "nombre_completo": full_name,
                "correo": nuevo_correo
            }
        },
        status_code=200
    )
