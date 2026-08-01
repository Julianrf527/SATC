"""Gestión de usuarios por administradores: alta, listado, estado y rol."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, insert, update
from pydantic import BaseModel, EmailStr, validator
from utils import emailUtil
from dotenv import load_dotenv
import string
import random
import logging
import os

#----- DB -----
from db.deps import get_db_managed
from db.models.usuario import Usuario
from db.models.permiso import Permiso
from db.models.rol import Rol
from core.permissions import Permisos

router = APIRouter()
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
PERMISO_USER = Permisos.PERMISO_USER
GESTION_USER = Permisos.GESTION_USER

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

#----------- FUNCIONES ----------
from utils.verify_token import verify_gateway_token
from utils.permission_crud import get_role_permissions, get_permissions_by_rol_id
from utils.insertLog import insert_auditoria
from utils.passwords import hash_password


async def _get_user_perm_names(rol_id: int, db: AsyncSession) -> set[str]:
    """Obtiene nombres de permisos del rol desde BD."""
    perms = await get_permissions_by_rol_id(rol_id, db)
    return {p["name"] for p in perms}

# ---------- MODELOS ----------

class User(BaseModel):
    first_name: str
    middle_name: str = ""
    lastname: str
    second_lastname: str = ""
    document: int
    email: EmailStr
    rol: int

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

    @validator('document')
    def validate_document(cls, v):
        """Valida el documento"""
        if v < 100000:
            raise ValueError('El documento debe tener al menos 6 dígitos')
        if v > 9999999999:
            raise ValueError('El documento no puede exceder 10 dígitos')
        return v

    @validator('email')
    def validate_email_lowercase(cls, v):
        """Convierte el email a minúsculas"""
        return v.lower() if v else v

    @validator('rol')
    def validate_rol(cls, v):
        """Valida que el rol sea válido"""
        if v <= 0:
            raise ValueError('Debe seleccionar un rol válido')
        return v

# ---------- ENDPOINTS ----------

@router.post("/register")
async def registrar_usuario(
    request: Request,
    data: User,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if PERMISO_USER not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para crear usuarios"
        )

    rol = data.rol

    rol_exists = await db.execute(select(exists().where(Rol.id == rol)))
    if not rol_exists.scalar():
        raise HTTPException(status_code=404, detail="El rol seleccionado no existe")

    # Anti escalada: nadie puede crear un usuario con un rol que tenga permisos
    # que el creador no posee.
    creator_perm_ids = await get_role_permissions(token_data["rol_id"], db)
    role_permission_ids = await get_role_permissions(rol, db)
    permisos_no_autorizados = role_permission_ids - creator_perm_ids

    if permisos_no_autorizados:
        stmt = select(Permiso.nombre).where(Permiso.id.in_(permisos_no_autorizados))
        result = await db.execute(stmt)
        nombres_permisos = result.scalars().all()
        raise HTTPException(
            status_code=403,
            detail=f"No puede asignar un rol con permisos que no posee: {', '.join(sorted(nombres_permisos))}"
        )

    def capitalize_name(name: str) -> str:
        return name.strip().capitalize() if name else ""

    first_name = capitalize_name(data.first_name)
    middle_name = capitalize_name(data.middle_name) if data.middle_name else ""
    lastname = capitalize_name(data.lastname)
    second_lastname = capitalize_name(data.second_lastname) if data.second_lastname else ""

    full_name_parts = [first_name]
    if middle_name:
        full_name_parts.append(middle_name)
    full_name_parts.append(lastname)
    if second_lastname:
        full_name_parts.append(second_lastname)
    full_name = " ".join(full_name_parts)

    document = data.document
    email = data.email.lower()
    rol = data.rol

    mayuscula = random.choice(string.ascii_uppercase)
    numeros = random.choices(string.digits, k=2)
    simbolo = random.choice("!@#$%^&*()-_=+?¿¡[]{}<>")

    restantes = 10 - (1 + 2 + 1)
    otros = random.choices(string.ascii_letters + string.digits, k=restantes)

    cont_list = list(mayuscula + "".join(numeros) + simbolo + "".join(otros))
    random.shuffle(cont_list)
    password_plain = "".join(cont_list)
    password_hashed = hash_password(password_plain)

    exist_doc = await db.execute(select(exists().where(Usuario.numero_documento == document)))
    if exist_doc.scalar():
        raise HTTPException(status_code=409, detail="El número de documento ya está registrado")

    exist_email = await db.execute(select(exists().where(Usuario.correo == email)))
    if exist_email.scalar():
        raise HTTPException(status_code=409, detail="El correo electrónico ya está registrado")

    stmt = insert(Usuario).values(
        numero_documento=document,
        primer_nombre=first_name,
        segundo_nombre=middle_name if middle_name else None,
        primer_apellido=lastname,
        segundo_apellido=second_lastname if second_lastname else None,
        correo=email,
        hash_contrasena=password_hashed,
        activo=True,
        rol_id=rol
    )
    await db.execute(stmt)

    datos_nuevos = {
        "numero_documento": document,
        "nombre_completo": full_name,
        "primer_nombre": first_name,
        "segundo_nombre": middle_name if middle_name else None,
        "primer_apellido": lastname,
        "segundo_apellido": second_lastname if second_lastname else None,
        "correo": email,
        "rol_id": rol,
        "activo": True
    }

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
        tipo_evento="GESTION_USUARIO",
        resultado="EXITOSO",
        detalle=f"Creación de usuario {full_name} con documento {document}",
        datos_nuevos=datos_nuevos
    )

    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error al guardar registro de auditoría"
        )

    # Commit antes del email: el envío puede fallar y no debe abortar el alta.
    await db.commit()

    try:
        message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <p>Hola <strong>{full_name}</strong>,</p>
            <p>Tu cuenta ha sido creada exitosamente. A continuación encontrarás tu contraseña temporal:</p>
            <div style="background: #f0f0f0; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                <p style="font-size: 18px; font-weight: bold; color: #2c3e50; letter-spacing: 2px; margin: 0;">
                    {password_plain}
                </p>
            </div>
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #856404;">
                    <strong>⚠️ Importante:</strong> Por tu seguridad, debes cambiar esta contraseña inmediatamente al iniciar sesión por primera vez.
                </p>
            </div>
            <p>Datos de acceso:</p>
            <ul>
                <li><strong>Correo:</strong> {email}</li>
                <li><strong>Contraseña temporal:</strong> (ver arriba)</li>
            </ul>
            <p>Si tienes alguna pregunta, no dudes en contactar al administrador.</p>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="color: #7f8c8d; font-size: 12px;">
                Este es un mensaje automático, por favor no responder a este correo.
            </p>
        </div>
        """
        await emailUtil.sendEmail(
            "Bienvenido al Sistema de Gestión de Expedientes",
            message,
            email,
            "Bienvenido al Sistema"
        )
    except Exception as e:
        logger.warning(f"No se pudo enviar el email de bienvenida a {email}: {str(e)}")

    return JSONResponse({"ok": True, "message": "Usuario registrado exitosamente"}, status_code=201)

@router.get("/all")
async def obtener_usuarios(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if PERMISO_USER not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para ver los usuarios"
        )

    stmr = select(
        Usuario.id,
        Usuario.numero_documento,
        Usuario.primer_nombre,
        Usuario.segundo_nombre,
        Usuario.primer_apellido,
        Usuario.segundo_apellido,
        Usuario.correo,
        Usuario.rol_id,
        Usuario.activo
    )
    result = await db.execute(stmr)
    users = result.all()

    user_list = [
        {
            "id": user.id,
            "numero_documento": user.numero_documento,
            "primer_nombre": user.primer_nombre,
            "segundo_nombre": user.segundo_nombre,
            "primer_apellido": user.primer_apellido,
            "segundo_apellido": user.segundo_apellido,
            "correo": user.correo,
            "rol_id": user.rol_id,
            "state": user.activo
        }
        for user in users
    ]

    return JSONResponse(content={"ok": True, "data": user_list}, status_code=200)

@router.patch("/toggleState/{user_id}")
async def actualizar_estado(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if GESTION_USER not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para actualizar el estado de los usuarios"
        )

    stmr = select(Usuario.activo, Usuario.numero_documento).where(Usuario.id == user_id)
    result = await db.execute(stmr)
    row = result.first()

    if row is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    current_state, numero_documento = row.activo, row.numero_documento

    datos_anteriores = {"user_id": user_id, "numero_documento": numero_documento, "activo": current_state}

    await db.execute(update(Usuario).where(Usuario.id == user_id).values(activo=not current_state))

    datos_nuevos = {"user_id": user_id, "numero_documento": numero_documento, "activo": not current_state}

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
        tipo_evento="DESACTIVACION" if current_state else "ACTIVACION",
        resultado="EXITOSO",
        detalle=f"Cambio de estado de usuario ID {user_id}: {current_state} → {not current_state}",
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos
    )

    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()
    return JSONResponse({"ok": True}, status_code=200)

@router.patch("/toggleRol/{user_id}/{rol_id}")
async def actualizar_rol_usuario(
    request: Request,
    user_id: int,
    rol_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if GESTION_USER not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para actualizar el rol de los usuarios"
        )

    usuario = await db.scalar(select(Usuario).where(Usuario.id == user_id))
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    rol_exists = await db.scalar(select(exists().where(Rol.id == rol_id)))
    if not rol_exists:
        raise HTTPException(status_code=404, detail="El rol seleccionado no existe")

    # Anti escalada: no se puede asignar un rol con permisos que el actor no tiene.
    user_permissions = await get_role_permissions(token_data["rol_id"], db)
    role_permissions = await get_role_permissions(rol_id, db)
    permisos_no_autorizados = role_permissions - user_permissions

    if permisos_no_autorizados:
        stmt_names = select(Permiso.nombre).where(Permiso.id.in_(permisos_no_autorizados))
        result_names = await db.execute(stmt_names)
        nombres = result_names.scalars().all()
        raise HTTPException(
            status_code=403,
            detail=f"No puede asignar un rol con permisos que no posee: {', '.join(nombres)}"
        )

    datos_anteriores = {"user_id": user_id, "rol_id": usuario.rol_id}

    await db.execute(update(Usuario).where(Usuario.id == user_id).values(rol_id=rol_id))

    datos_nuevos = {"user_id": user_id, "rol_id": rol_id}

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
        tipo_evento="CAMBIO_ROL",
        resultado="EXITOSO",
        detalle=f"Cambio de rol del usuario ID {user_id}: {usuario.rol_id} → {rol_id}",
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos
    )

    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()
    return JSONResponse({"ok": True, "msg": "Rol actualizado correctamente"}, status_code=200)
