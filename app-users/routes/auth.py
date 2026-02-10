from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.dialects.postgresql import insert
from pydantic import BaseModel, EmailStr, validator
from passlib.hash import bcrypt
from utils.passwords import hash_password, verify_password
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from dotenv import load_dotenv
from jose import jwt
import traceback
import random
import string
import logging
import os

#----- DB -----
from db.deps import get_db
from db.models.rol import Rol
from db.models.rol_permiso import RolPermiso
from db.models.permiso import Permiso
from db.models.usuario import Usuario
from db.models.codigo_recuperacion import CodigoRecuperacion

router = APIRouter()

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_KEY_GATEWAY = os.getenv("SECRET_KEY_GATEWAY")  # Para que el gateway pueda leer el JWT
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXP_DAYS = os.getenv("JWT_EXP_DAYS")

# Validar que las claves secretas estén cargadas
if not SECRET_KEY_GATEWAY:
    raise RuntimeError("SECRET_KEY_GATEWAY no está configurada en el archivo .env")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no está configurada en el archivo .env")

#----------- FUNCIONES ------------

from utils.verify_gateway_token import verify_gateway_token
from utils.insertLog import insert_auditoria
from utils.emailUtil import sendEmail

#----------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- MODELOS ----------

class LoginData(BaseModel):
    email: EmailStr
    password: str
    remember: bool = False

class RecuperarRequest(BaseModel):
    email: EmailStr 
    code: Optional[str] = None
    new_password: Optional[str] = None

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

@router.post("/login")
async def iniciar_sesion(
    data: LoginData, 
    db: AsyncSession = Depends(get_db)
):
    try:
        email = data.email
        password = data.password
        remember = data.remember 
        
        # Buscar al usuario
        stmt = select(
            Usuario.numero_documento,
            Usuario.rol_id,
            Usuario.primer_nombre,
            Usuario.segundo_nombre,
            Usuario.primer_apellido,
            Usuario.segundo_apellido,
            Usuario.hash_contrasena,
            Usuario.activo
        ).where(Usuario.correo == email)

        result = await db.execute(stmt)
        user = result.first()
        if user is None:
            raise HTTPException(status_code=401, detail="Usuario no registrado")
        
        if not user[7]:
            raise HTTPException(status_code=403, detail="Usuario inactivo")

        if user and verify_password(password, user[6]):
            user_id = user[0]
            rol_id = user[1]

            # Construir nombre completo
            nombre_partes = [user[2]]
            if user[3]:
                nombre_partes.append(user[3])
            nombre_partes.append(user[4])
            if user[5]:
                nombre_partes.append(user[5])
            nombre_completo = " ".join(nombre_partes)

            # Obtener rol name
            stmt = (
                select(Rol.nombre).where(Rol.id == rol_id)
            )
            result = await db.execute(stmt)
            rol_name = result.first()[0]

            # Obtener permisos del rol
            if rol_name:
                stmt = (
                select(Permiso.nombre, Permiso.menu_path)
                .join(RolPermiso, 
                        and_(RolPermiso.permiso_id == Permiso.id,
                            RolPermiso.rol_id == rol_id)
                    )
                    .distinct()
                )
                result = await db.execute(stmt)
                permissions = result.all()

            permisos = [
                {"name": permi[0], "path": permi[1]}
                for permi in permissions
            ]

            # Crear payload del token
            token_data = {
                "id": str(user_id),
                "primer_nombre": user[2],
                "segundo_nombre": user[3],
                "primer_apellido": user[4],
                "segundo_apellido": user[5],
                "correo": email,
                "rol": rol_name,
                "permisos": permisos
            }

            # Firmar con SECRET_KEY_GATEWAY para que el gateway pueda leerlo
            token = jwt.encode(token_data, SECRET_KEY_GATEWAY, algorithm=JWT_ALGORITHM)

            # Actualizar último ingreso
            stmt = update(Usuario).where(Usuario.correo == email).values(ultimo_ingreso=datetime.utcnow())
            await db.execute(stmt)

            # Guardar auditoría de inicio de sesión
            datos_nuevos = {
                "usuario_id": user_id,
                "nombre_completo": nombre_completo,
                "correo": email,
                "rol": rol_name,
                "remember": remember,
                "fecha_login": datetime.now(ZoneInfo("America/Bogota")).isoformat()
            }

            audit_result = await insert_auditoria(
                db=db,
                usuario_id=user_id,
                tabla_afectada="usuario",
                tipo_operacion="UPDATE",
                descripcion=f"Inicio de sesión de usuario {nombre_completo}",
                id_registro=str(user_id),
                datos_nuevos=datos_nuevos
            )

            if not audit_result["ok"]:
                await db.rollback()
                raise HTTPException(
                    status_code=500,
                    detail="Error al guardar registro de auditoría"
                )

            await db.commit()

            # Preparar respuesta con cookie
            response = JSONResponse(content={"ok": True}, status_code=200)
            cookie_options = {
                "key": "access_token",
                "value": token,
                "httponly": True,
                "samesite": "Lax",
                "secure": False
            }
            
            if remember:
                cookie_options["max_age"] = int(timedelta(days=int(JWT_EXP_DAYS)).total_seconds())

            response.set_cookie(**cookie_options)
            return response

        raise HTTPException(status_code=401, detail="Credenciales Invalidas")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor durante login: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error en el servidor")

@router.post("/recovery")
async def validar_correo(
    data: RecuperarRequest, 
    db: AsyncSession = Depends(get_db)
):  
    email = data.email
    try:
        # Obtener el usuario y su nombre
        stmt = select(
            Usuario.numero_documento,
            Usuario.primer_nombre,
            Usuario.primer_apellido
        ).where(Usuario.correo == email)
        result = await db.execute(stmt)
        user_data = result.first()
        
        if user_data is None:
            raise HTTPException(status_code=404, detail="Correo no registrado")
        
        user_id = user_data[0]
        user_name = f"{user_data[1]} {user_data[2]}"

        # Verificar si ya existe código activo
        stmt = select(CodigoRecuperacion.id).where(
            and_(
                CodigoRecuperacion.usuario_id == user_id,
                CodigoRecuperacion.fecha_expiracion > func.now()
            )
        )
        codigo_existente = await db.scalar(stmt)
        if codigo_existente:
            return JSONResponse(
                content={"ok": True, "message": "Ya cuenta con código, valide su correo"},
                status_code=200
            )

        # Generar nuevo código
        caracteres = string.ascii_uppercase + string.digits
        code = ''.join(random.choices(caracteres, k=5))

        # Enviar correo con formato mejorado
        message = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <p>Hola <strong>{user_name}</strong>,</p>
            <p>Hemos recibido una solicitud para recuperar tu contraseña. Utiliza el siguiente código para continuar con el proceso:</p>
            <div style="background: #f0f0f0; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                <p style="font-size: 24px; font-weight: bold; color: #2c3e50; letter-spacing: 4px; margin: 0;">
                    {code}
                </p>
            </div>
            <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 20px 0;">
                <p style="margin: 0; color: #856404;">
                    <strong>⚠️ Importante:</strong> Este código solo puede usarse una vez y expirará en <strong>10 minutos</strong>.<br>
                    Si no lo utilizas dentro de ese tiempo, deberás solicitar uno nuevo.
                </p>
            </div>
        </div>
        """
        await sendEmail(
            "Recuperación de Contraseña",
            message,
            email,
            "Recuperación de Contraseña"
        )

        # Guardar/actualizar código (UPSERT)
        codigo_hash = hash_password(code)
        fecha_exp = datetime.now(ZoneInfo("America/Bogota")) + timedelta(minutes=10)
        
        stmt = insert(CodigoRecuperacion).values(
            usuario_id=user_id,
            codigo=codigo_hash,
            fecha_expiracion=fecha_exp
        ).on_conflict_do_update(
            index_elements=["usuario_id"],
            set_={
                "codigo": codigo_hash,
                "fecha_expiracion": fecha_exp
            }
        )
        await db.execute(stmt)
        await db.flush()

        # Obtener el ID del registro (nuevo o actualizado)
        stmt = select(CodigoRecuperacion.id).where(
            CodigoRecuperacion.usuario_id == user_id
        )
        code_id = await db.scalar(stmt)

        # Guardar auditoría
        datos_nuevos = {
            "correo": email,
            "usuario_id": user_id,
            "fecha_solicitud": datetime.now(ZoneInfo("America/Bogota")).isoformat(),
            "expiracion_minutos": 10
        }
        
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tabla_afectada="codigo_recuperacion",
            tipo_operacion="INSERT",
            descripcion=f"Solicitud de código de recuperación para {email}",
            id_registro=str(code_id),
            datos_nuevos=datos_nuevos
        )
        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(status_code=500, detail="Error al guardar auditoría")

        await db.commit()

        return JSONResponse(
            content={"ok": True, "message": "Revisa tu correo para continuar"},
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error al enviar código a {email}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error en el servidor")

@router.post("/recovery-code")
async def validar_code_de_recuperacion(
    data: RecuperarRequest, 
    db: AsyncSession = Depends(get_db)
):  
    try:
        email = data.email
        code = data.code

        # Obtener datos del usuario
        stmt_user = select(
            Usuario.numero_documento,
            Usuario.primer_nombre,
            Usuario.primer_apellido
        ).where(Usuario.correo == email)
        result = await db.execute(stmt_user)
        user_data = result.first()
        
        if not user_data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        user_id = user_data[0]
        user_name = f"{user_data[1]} {user_data[2]}"

        # Verificar código
        stmr = select(
            CodigoRecuperacion.codigo
        ).where(and_(
            CodigoRecuperacion.usuario_id == user_id,
            CodigoRecuperacion.fecha_expiracion > datetime.now(ZoneInfo("America/Bogota"))
        ))
        result = await db.execute(stmr)
        result = result.first()

        if result and verify_password(code, result[0]):
            
            # Eliminar código usado
            stmr = delete(CodigoRecuperacion).where(
                and_(
                    CodigoRecuperacion.codigo == result[0],
                    CodigoRecuperacion.usuario_id == user_id
                )
            )
            await db.execute(stmr)
            
            # Generar contraseña temporal
            mayuscula = random.choice(string.ascii_uppercase)
            numeros = random.choices(string.digits, k=2)
            simbolo = random.choice("!@#$%^&*()-_=+?¿¡[]{}<>")
            
            restantes = 10 - (1 + 2 + 1)
            otros = random.choices(string.ascii_letters + string.digits, k=restantes)

            cont_list = list(mayuscula + "".join(numeros) + simbolo + "".join(otros))
            random.shuffle(cont_list)
            cont = "".join(cont_list)

            # Enviar correo con formato mejorado
            message = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <p>Hola <strong>{user_name}</strong>,</p>
                <p>Tu solicitud de recuperación de contraseña ha sido procesada exitosamente. A continuación encontrarás tu contraseña temporal:</p>
                <div style="background: #f0f0f0; padding: 15px; border-radius: 5px; text-align: center; margin: 20px 0;">
                    <p style="font-size: 18px; font-weight: bold; color: #2c3e50; letter-spacing: 2px; margin: 0;">
                        {cont}
                    </p>
                </div>
                <div style="background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin: 20px 0;">
                    <p style="margin: 0; color: #856404;">
                        <strong>⚠️ Importante:</strong> Por tu seguridad, te recomendamos cambiar esta contraseña inmediatamente después de iniciar sesión.
                    </p>
                </div>
                <p>Datos de acceso:</p>
                <ul>
                    <li><strong>Correo:</strong> {email}</li>
                    <li><strong>Contraseña temporal:</strong> (ver arriba)</li>
                </ul>
                <div style="background: #d1ecf1; border-left: 4px solid #17a2b8; padding: 12px; margin: 20px 0;">
                    <p style="margin: 0; color: #0c5460;">
                        <strong>💡 Consejo:</strong> Una vez dentro del sistema, ve a tu perfil para establecer una contraseña nueva y segura.
                    </p>
                </div>
            </div>
            """
            await sendEmail(
                "Contraseña Temporal",
                message,
                email,
                "Contraseña Temporal"
            )

            # Actualizar contraseña en la BD
            stmt = update(Usuario).where(Usuario.correo == email).values(hash_contrasena=hash_password(cont))
            await db.execute(stmt)

            # Guardar auditoría de recuperación exitosa
            datos_nuevos = {
                "correo": email,
                "usuario_id": user_id,
                "fecha_recuperacion": datetime.now(ZoneInfo("America/Bogota")).isoformat(),
                "password_temporal_enviado": True
            }

            audit_result = await insert_auditoria(
                db=db,
                usuario_id=user_id,
                tabla_afectada="usuario",
                tipo_operacion="UPDATE",
                descripcion=f"Recuperación de contraseña exitosa para {email}",
                id_registro=str(user_id),
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
                content={"ok": True, "message": "Revisa tu correo para continuar"},
                status_code=200
            )
        
        raise HTTPException(status_code=401, detail="Código inválido o expirado")
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.warning(f"Error en el servidor durante auth code: {e}") 
        raise HTTPException(status_code=500, detail="Error en el servidor")

@router.get("/me")
async def validar_token(
    request: Request
):
    try:
        verify_gateway_token(request)

        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Token no encontrado")

        # Decodificar con SECRET_KEY_GATEWAY (misma clave usada para firmar)
        payload = jwt.decode(token, SECRET_KEY_GATEWAY, algorithms=JWT_ALGORITHM)
        return JSONResponse({"ok": True, "usuario": payload}, status_code=200)
    except Exception as e:
        logger.error(f"Error en el servidor durante auth token: {e}")
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

@router.post("/logout")
async def cerrar_sesion(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
):  
    try:
        # Obtener información del usuario antes de cerrar sesión
        token = request.cookies.get("access_token")
        
        if token:
            try:
                # Decodificar con SECRET_KEY_GATEWAY (misma clave usada para firmar)
                payload = jwt.decode(token, SECRET_KEY_GATEWAY, algorithms=JWT_ALGORITHM)
                user_id = int(payload.get("id"))
                
                # Construir nombre completo
                nombre_partes = [payload.get("primer_nombre")]
                if payload.get("segundo_nombre"):
                    nombre_partes.append(payload.get("segundo_nombre"))
                nombre_partes.append(payload.get("primer_apellido"))
                if payload.get("segundo_apellido"):
                    nombre_partes.append(payload.get("segundo_apellido"))
                nombre_completo = " ".join([p for p in nombre_partes if p])

                # Guardar auditoría de cierre de sesión
                datos_anteriores = {
                    "usuario_id": user_id,
                    "nombre_completo": nombre_completo,
                    "correo": payload.get("correo"),
                    "rol": payload.get("rol"),
                    "fecha_logout": datetime.now(ZoneInfo("America/Bogota")).isoformat()
                }

                audit_result = await insert_auditoria(
                    db=db,
                    usuario_id=user_id,
                    tabla_afectada="usuario",
                    tipo_operacion="UPDATE",
                    descripcion=f"Cierre de sesión de usuario {nombre_completo}",
                    id_registro=str(user_id),
                    datos_anteriores=datos_anteriores
                )

                if not audit_result["ok"]:
                    logger.warning(f"No se pudo guardar auditoría de logout para usuario {user_id}")

                await db.commit()
            except Exception as e:
                logger.warning(f"Error al guardar auditoría de logout: {e}")

        response.delete_cookie(key="access_token", path="/")
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Error durante logout: {e}")
        response.delete_cookie(key="access_token", path="/")
        return {"ok": True}