from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.dialects.postgresql import insert
from pydantic import BaseModel, EmailStr, validator
from passlib.hash import bcrypt
from utils.passwords import hash_password, verify_password, verify_password_async
from utils.redis_session import (
    save_session_redis, 
    get_session_redis, 
    delete_session_redis,
    redis_health_check
)
from utils.rate_limiter import RateLimiter, LoginThrottler
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from dotenv import load_dotenv
from jose import jwt, jwe
import traceback
import random
import string
import logging
import os
import uuid
import json

#----- DB -----
from db.deps import get_db
from db.models.rol import Rol
from db.models.rol_permiso import RolPermiso
from db.models.permiso import Permiso
from db.models.usuario import Usuario
from db.models.codigo_recuperacion import CodigoRecuperacion
from db.models.sesion_activa import SesionActiva

router = APIRouter()

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_KEY_GATEWAY = os.getenv("SECRET_KEY_GATEWAY")  # Para que el gateway pueda leer el JWT
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXP_DAYS = os.getenv("JWT_EXP_DAYS")
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "10"))

# Validar que las claves secretas estén cargadas
if not SECRET_KEY_GATEWAY:
    raise RuntimeError("SECRET_KEY_GATEWAY no está configurada en el archivo .env")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no está configurada en el archivo .env")

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        email = data.email.lower()  # Normalizar inmediatamente
        password = data.password
        remember = data.remember 
        ip_address = request.client.host if request.client else "unknown"
        
        # ═══════════════════════════════════════════════════════════
        # SEGURIDAD 1: Verificar bloqueo por intentos fallidos
        # ═══════════════════════════════════════════════════════════
        block_status = LoginThrottler.check_login_block(f"{email}:{ip_address}")
        if block_status["blocked"]:
            retry_after = block_status["retry_after"] - int(time.time())
            logger.warning(f"🚫 Login bloqueado para {email[:3]}***@{email.split('@')[1]} desde {ip_address} - {block_status['attempts']} intentos")
            raise HTTPException(
                status_code=429,
                detail=f"Cuenta temporalmente bloqueada por múltiples intentos fallidos. Intente nuevamente en {retry_after // 60} minutos.",
                headers={"Retry-After": str(retry_after)}
            )
        
        # ═══════════════════════════════════════════════════════════
        # SEGURIDAD 2: Rate Limiting (protección contra brute force)
        # ═══════════════════════════════════════════════════════════
        rate_status = RateLimiter.check_rate_limit(ip_address, "login")
        if not rate_status["allowed"]:
            logger.warning(f"⚠️ Rate limit excedido para IP {ip_address} en login")
            raise HTTPException(
                status_code=429,
                detail=f"Demasiadas solicitudes. Intente nuevamente en {rate_status['retry_after']} segundos.",
                headers={"Retry-After": str(rate_status["retry_after"])}
            )
        
        # OPTIMIZACIÓN 1: SELECT solo campos críticos
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
        
        # Validaciones rápidas (fail-fast)
        if user is None:
            # Registrar intento fallido
            LoginThrottler.record_failed_login(f"{email}:{ip_address}")
            logger.info(f"❌ Login fallido: usuario no existe - {email[:3]}***@{email.split('@')[1]} desde {ip_address}")
            raise HTTPException(status_code=401, detail="Usuario no registrado")
        
        if not user[7]:  # activo
            logger.info(f"❌ Login fallido: usuario inactivo - {email[:3]}***@{email.split('@')[1]}")
            raise HTTPException(status_code=403, detail="Usuario inactivo")

        # OPTIMIZACIÓN 2: bcrypt async (no bloquea event loop)
        password_valid = await verify_password_async(password, user[6])
        if not password_valid:
            # Registrar intento fallido y aplicar throttling
            throttle_status = LoginThrottler.record_failed_login(f"{email}:{ip_address}")
            logger.warning(f"❌ Login fallido: contraseña incorrecta - {email[:3]}***@{email.split('@')[1]} desde {ip_address} - Intento #{throttle_status['attempts']}")
            
            if throttle_status["blocked"]:
                retry_minutes = throttle_status["block_duration"] // 60
                raise HTTPException(
                    status_code=429,
                    detail=f"Demasiados intentos fallidos. Cuenta bloqueada por {retry_minutes} minutos.",
                    headers={"Retry-After": str(throttle_status["block_duration"])}
                )
            
            raise HTTPException(status_code=401, detail="Credenciales Invalidas")
        
        user_id = user[0]
        rol_id = user[1]
        token_jti = str(uuid.uuid4())

        # Obtener permisos del rol para incluirlos en el token
        permisos = []
        if rol_id:
            stmt_permisos = select(Permiso.nombre, Permiso.menu_path).join(
                RolPermiso, RolPermiso.permiso_id == Permiso.id
            ).where(RolPermiso.rol_id == rol_id)
            result_permisos = await db.execute(stmt_permisos)
            permisos = [
                {"name": nombre, "path": menu_path}
                for nombre, menu_path in result_permisos.all()
            ]

        token_data = {
            "id": str(user_id),
            "primer_nombre": user[2],
            "segundo_nombre": user[3] or "",
            "primer_apellido": user[4],
            "segundo_apellido": user[5] or "",
            "correo": email,
            "rol_id": rol_id,
            "permisos": permisos,
            "jti": token_jti
        }

        # ═══════════════════════════════════════════════════════════
        # PRODUCCIÓN: Encriptar payload con JWE (JSON Web Encryption)
        # ═══════════════════════════════════════════════════════════
        token = jwe.encrypt(
            plaintext=json.dumps(token_data).encode('utf-8'),
            key=SECRET_KEY_GATEWAY,
            algorithm='dir',  # Direct Encryption with symmetric key
            encryption='A256GCM'  # AES-256-GCM (AEAD)
        ).decode('utf-8')

        # OPTIMIZACIÓN 4: Guardar sesión en REDIS (96% más rápido que PostgreSQL)
        # TTL automático: no necesita cleanup periódico
        ip_address = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        ttl_days = int(JWT_EXP_DAYS) if remember else 1
        
        redis_saved = await save_session_redis(
            token_jti=token_jti,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            ttl_days=ttl_days
        )
        
        # Fallback a PostgreSQL si Redis falla
        if not redis_saved:
            logger.warning(f"⚠️ Redis no disponible, guardando sesión en PostgreSQL")
            nueva_sesion = SesionActiva(
                usuario_id=user_id,
                token_jti=token_jti,
                ip_address=ip_address,
                user_agent=user_agent,
                activo=True
            )
            db.add(nueva_sesion)
            await db.commit()
        
        # ═══════════════════════════════════════════════════════════
        # SEGURIDAD 3: Resetear intentos fallidos después de login exitoso
        # ═══════════════════════════════════════════════════════════
        LoginThrottler.reset_failed_logins(f"{email}:{ip_address}")
        logger.info(f"✅ Login exitoso: {email[:3]}***@{email.split('@')[1]} desde {ip_address}")

        # OPTIMIZACIÓN 5: Respuesta simplificada
        response = JSONResponse({"ok": True}, 200)
        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            samesite="Lax",
            secure=False,  # Cambiado a False para desarrollo (HTTP)
            max_age=int(timedelta(days=int(JWT_EXP_DAYS)).total_seconds()) if remember else None
        )
        return response

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
        try:
            await sendEmail(
                "Recuperación de Contraseña",
                message,
                email,
                "Recuperación de Contraseña"
            )
        except Exception as mail_err:
            logger.error(f"No se pudo enviar correo a {email}: {mail_err}")

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
            try:
                await sendEmail(
                    "Contraseña Temporal",
                    message,
                    email,
                    "Contraseña Temporal"
                )
            except Exception as mail_err:
                logger.error(f"No se pudo enviar correo a {email}: {mail_err}")

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
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Verificar que venga del gateway (opcional para /me)
        gw_token = request.headers.get("x-gateway-token")
        if gw_token and gw_token != os.getenv("SECRET_GATEWAY"):
            raise HTTPException(status_code=403, detail="Gateway token inválido")

        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="Token no encontrado")

        # ═══════════════════════════════════════════════════════════
        # PRODUCCIÓN: Desencriptar payload JWE
        # ═══════════════════════════════════════════════════════════
        try:
            # Intentar desencriptar con JWE (tokens de producción)
            decrypted_payload = jwe.decrypt(token, SECRET_KEY_GATEWAY)
            payload = json.loads(decrypted_payload.decode('utf-8'))
        except Exception as jwe_error:
            # Fallback: Intentar decodificar JWT sin encriptar (tokens legacy)
            try:
                payload = jwt.decode(token, SECRET_KEY_GATEWAY, algorithms=JWT_ALGORITHM)
                logger.warning(f"⚠️ Token sin encriptar detectado. Migrar a JWE.")
            except Exception as jwt_error:
                logger.error(f"❌ Error decodificando token: {jwe_error}, {jwt_error}")
                raise HTTPException(401, "Token inválido o corrupto")
        
        # ═══════════════════════════════════════════════════════════
        # CONSULTAR PERMISOS DEL ROL DEL USUARIO
        # ═══════════════════════════════════════════════════════════
        rol_id = payload.get("rol_id")
        if rol_id:
            # Obtener nombre del rol
            stmt = select(Rol.nombre).where(Rol.id == rol_id)
            result = await db.execute(stmt)
            rol_nombre = result.scalar_one_or_none()
            
            # Obtener permisos del rol con sus rutas
            stmt = select(
                Permiso.nombre,
                Permiso.menu_path
            ).join(
                RolPermiso, RolPermiso.permiso_id == Permiso.id
            ).where(
                RolPermiso.rol_id == rol_id
            )
            result = await db.execute(stmt)
            permisos_rows = result.all()
            
            # Formatear permisos para el frontend
            permisos = [
                {"name": nombre, "path": menu_path}
                for nombre, menu_path in permisos_rows
            ]
            
            # Agregar datos al payload
            payload["rol"] = rol_nombre
            payload["permisos"] = permisos
        else:
            # Si no hay rol_id, devolver listas vacías
            payload["rol"] = None
            payload["permisos"] = []
        
        return JSONResponse({"ok": True, "usuario": payload}, status_code=200)
    except Exception as e:
        logger.error(f"Error en el servidor durante auth token: {e}")
        raise HTTPException(status_code=401, detail="Credenciales invalidas")

@router.post("/validate-session")
async def validar_sesion_activa(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint interno para que el gateway valide si un JTI está activo.
    Solo debe ser llamado desde el gateway con el token de servicio.
    """
    try:
        from utils.verify_gateway_token import verify_service_token
        verify_service_token(request)
        
        # Obtener el JTI del body
        body = await request.json()
        jti = body.get("jti")
        
        if not jti:
            return JSONResponse({"valid": False, "reason": "JTI no proporcionado"}, status_code=200)
        
        # Buscar la sesión en la base de datos
        stmt = select(SesionActiva).where(
            and_(
                SesionActiva.token_jti == jti,
                SesionActiva.activo == True
            )
        )
        result = await db.execute(stmt)
        sesion = result.scalar_one_or_none()
        
        if sesion:
            # Actualizar fecha de último uso
            stmt = update(SesionActiva).where(
                SesionActiva.token_jti == jti
            ).values(fecha_ultimo_uso=datetime.now(ZoneInfo("America/Bogota")))
            await db.execute(stmt)
            await db.commit()
            
            return JSONResponse({"valid": True}, status_code=200)
        else:
            return JSONResponse({"valid": False, "reason": "Sesión no encontrada o inactiva"}, status_code=200)
            
    except Exception as e:
        logger.error(f"Error validando sesión activa: {e}")
        return JSONResponse({"valid": False, "reason": "Error interno"}, status_code=200)

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
                # ═══════════════════════════════════════════════════════════
                # PRODUCCIÓN: Desencriptar payload JWE
                # ═══════════════════════════════════════════════════════════
                try:
                    # Intentar desencriptar con JWE (tokens de producción)
                    decrypted_payload = jwe.decrypt(token, SECRET_KEY_GATEWAY)
                    payload = json.loads(decrypted_payload.decode('utf-8'))
                except Exception as jwe_error:
                    # Fallback: Intentar decodificar JWT sin encriptar (tokens legacy)
                    try:
                        payload = jwt.decode(token, SECRET_KEY_GATEWAY, algorithms=JWT_ALGORITHM)
                        logger.warning(f"⚠️ Token sin encriptar detectado en validate-session")
                    except Exception as jwt_error:
                        logger.error(f"❌ Error decodificando token: {jwe_error}")
                        return JSONResponse({"ok": False, "valid": False, "message": "Token inválido"}, 401)
                user_id = int(payload.get("id"))
                token_jti = payload.get("jti")
                
                # Invalidar la sesión activa en la base de datos
                if token_jti:
                    stmt = update(SesionActiva).where(
                        SesionActiva.token_jti == token_jti
                    ).values(activo=False)
                    await db.execute(stmt)
                
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