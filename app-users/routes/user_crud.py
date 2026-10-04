"""Gestión de usuarios por administradores: alta, listado, estado y rol."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, insert, update
from pydantic import BaseModel, EmailStr, validator
from utils import emailUtil
from dotenv import load_dotenv
from typing import Optional
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
from utils.passwords import hash_password, generate_temp_password
from utils.redis_session import get_redis_client


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


class AdminUserUpdate(BaseModel):
    """Actualización parcial: solo se aplican los campos que llegan (no None)."""
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    lastname: Optional[str] = None
    second_lastname: Optional[str] = None
    document: Optional[int] = None
    email: Optional[EmailStr] = None
    rol_id: Optional[int] = None
    activo: Optional[bool] = None

    @validator('first_name', 'lastname')
    def validate_required_names(cls, v):
        """first_name/lastname, si llegan, no pueden llegar vacíos."""
        if v is not None and not v.strip():
            raise ValueError('Este campo no puede estar vacío')
        return v

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
        if v is None:
            return v
        if v < 100000:
            raise ValueError('El documento debe tener al menos 6 dígitos')
        if v > 9999999999:
            raise ValueError('El documento no puede exceder 10 dígitos')
        return v

    @validator('email')
    def validate_email_lowercase(cls, v):
        """Convierte el email a minúsculas"""
        return v.lower() if v else v

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

    password_plain = generate_temp_password()
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

@router.patch("/{user_id}")
async def admin_actualizar_usuario(
    request: Request,
    user_id: int,
    data: AdminUserUpdate,
    db: AsyncSession = Depends(get_db_managed),
):
    """Actualización parcial de un usuario por un admin: documento, nombres, correo, rol y/o estado.
    Solo se tocan los campos enviados y que realmente cambian (contraseña no se maneja aquí)."""
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if GESTION_USER not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para editar los usuarios"
        )

    usuario = await db.scalar(select(Usuario).where(Usuario.id == user_id))
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    def capitalize_name(name: str) -> str:
        return name.strip().capitalize() if name else ""

    valores = {}
    datos_anteriores = {}
    datos_nuevos = {}

    if data.rol_id is not None and data.rol_id != usuario.rol_id:
        rol_exists = await db.scalar(select(exists().where(Rol.id == data.rol_id)))
        if not rol_exists:
            raise HTTPException(status_code=404, detail="El rol seleccionado no existe")

        # Anti escalada: no se puede asignar un rol con permisos que el actor no tiene.
        user_permissions = await get_role_permissions(token_data["rol_id"], db)
        role_permissions = await get_role_permissions(data.rol_id, db)
        permisos_no_autorizados = role_permissions - user_permissions
        if permisos_no_autorizados:
            stmt_names = select(Permiso.nombre).where(Permiso.id.in_(permisos_no_autorizados))
            result_names = await db.execute(stmt_names)
            nombres = result_names.scalars().all()
            raise HTTPException(
                status_code=403,
                detail=f"No puede asignar un rol con permisos que no posee: {', '.join(sorted(nombres))}"
            )

        valores["rol_id"] = data.rol_id
        datos_anteriores["rol_id"] = usuario.rol_id
        datos_nuevos["rol_id"] = data.rol_id

    if data.activo is not None and data.activo != usuario.activo:
        valores["activo"] = data.activo
        datos_anteriores["activo"] = usuario.activo
        datos_nuevos["activo"] = data.activo

    if data.document is not None and data.document != usuario.numero_documento:
        exist_doc = await db.scalar(select(exists().where(
            Usuario.numero_documento == data.document, Usuario.id != user_id
        )))
        if exist_doc:
            raise HTTPException(status_code=409, detail="El número de documento ya está registrado")
        valores["numero_documento"] = data.document
        datos_anteriores["numero_documento"] = usuario.numero_documento
        datos_nuevos["numero_documento"] = data.document

    if data.email is not None and data.email.lower() != usuario.correo:
        email = data.email.lower()
        exist_email = await db.scalar(select(exists().where(
            Usuario.correo == email, Usuario.id != user_id
        )))
        if exist_email:
            raise HTTPException(status_code=409, detail="El correo electrónico ya está registrado")
        valores["correo"] = email
        datos_anteriores["correo"] = usuario.correo
        datos_nuevos["correo"] = email

    if data.first_name is not None:
        first_name = capitalize_name(data.first_name)
        if first_name != usuario.primer_nombre:
            valores["primer_nombre"] = first_name
            datos_anteriores["primer_nombre"] = usuario.primer_nombre
            datos_nuevos["primer_nombre"] = first_name

    if data.lastname is not None:
        lastname = capitalize_name(data.lastname)
        if lastname != usuario.primer_apellido:
            valores["primer_apellido"] = lastname
            datos_anteriores["primer_apellido"] = usuario.primer_apellido
            datos_nuevos["primer_apellido"] = lastname

    if data.middle_name is not None:
        middle_name = capitalize_name(data.middle_name) or None
        if middle_name != usuario.segundo_nombre:
            valores["segundo_nombre"] = middle_name
            datos_anteriores["segundo_nombre"] = usuario.segundo_nombre
            datos_nuevos["segundo_nombre"] = middle_name

    if data.second_lastname is not None:
        second_lastname = capitalize_name(data.second_lastname) or None
        if second_lastname != usuario.segundo_apellido:
            valores["segundo_apellido"] = second_lastname
            datos_anteriores["segundo_apellido"] = usuario.segundo_apellido
            datos_nuevos["segundo_apellido"] = second_lastname

    if not valores:
        return JSONResponse({"ok": True, "message": "No se realizaron cambios"}, status_code=200)

    await db.execute(update(Usuario).where(Usuario.id == user_id).values(**valores))

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
        tipo_evento="EDICION_USUARIO",
        resultado="EXITOSO",
        detalle=f"Edición administrativa del usuario ID {user_id}: {', '.join(valores.keys())}",
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
    )

    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    return JSONResponse({
        "ok": True,
        "message": "Usuario actualizado correctamente",
        "data": datos_nuevos,
    }, status_code=200)

@router.post("/resend-password/{user_id}")
async def reenviar_contrasena(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db_managed),
):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if GESTION_USER not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para reenviar contraseñas"
        )

    usuario = await db.scalar(select(Usuario).where(Usuario.id == user_id))
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    password_plain = generate_temp_password()
    password_hashed = hash_password(password_plain)

    await db.execute(update(Usuario).where(Usuario.id == user_id).values(hash_contrasena=password_hashed))

    # La contraseña cambió: se invalida la sesión activa para forzar reingreso.
    r = get_redis_client()
    if r:
        await r.delete(f"session:user:{user_id}")
    else:
        logger.warning("Redis no disponible, no se pudo eliminar sesión tras reenvío de contraseña")

    full_name = f"{usuario.primer_nombre} {usuario.primer_apellido}"

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
        tipo_evento="REENVIO_CONTRASENA",
        resultado="EXITOSO",
        detalle=f"Reenvío de contraseña temporal para usuario ID {user_id} ({full_name}), iniciado por administrador",
        datos_nuevos={"user_id": user_id, "correo": usuario.correo},
    )

    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar registro de auditoría")

    await db.commit()

    email_sent = True
    try:
        message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <p>Hola <strong>{full_name}</strong>,</p>
            <p>Un administrador ha generado una nueva contraseña temporal para tu cuenta. A continuación la encontrarás:</p>
            <div style="background: #f0f0f0; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                <p style="font-size: 18px; font-weight: bold; color: #2c3e50; letter-spacing: 2px; margin: 0;">
                    {password_plain}
                </p>
            </div>
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #856404;">
                    <strong>⚠️ Importante:</strong> Por tu seguridad, debes cambiar esta contraseña inmediatamente al iniciar sesión.
                </p>
            </div>
            <p>Tu sesión activa fue cerrada por este cambio.</p>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="color: #7f8c8d; font-size: 12px;">
                Este es un mensaje automático, por favor no responder a este correo.
            </p>
        </div>
        """
        await emailUtil.sendEmail(
            "Contraseña temporal reenviada",
            message,
            usuario.correo,
            "Contraseña Temporal Reenviada"
        )
    except Exception as e:
        email_sent = False
        logger.warning(f"No se pudo reenviar el email de contraseña temporal a {usuario.correo}: {str(e)}")

    return JSONResponse({
        "ok": True,
        "email_sent": email_sent,
        "message": "Contraseña reenviada correctamente" if email_sent else "Contraseña actualizada, pero el envío del correo falló",
    }, status_code=200)
