from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.dialects.postgresql import insert
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from dotenv import load_dotenv
from jose import jwe
import traceback
import time
import random
import string
import logging
import os
import uuid
import json
import asyncio

#----- DB -----
from db.deps import get_db_managed
from db.models.rol import Rol
from db.models.rol_permiso import RolPermiso
from db.models.permiso import Permiso
from db.models.usuario import Usuario
from db.models.codigo_recuperacion import CodigoRecuperacion

router = APIRouter()

# Fail-safe en True: solo se desactiva explícitamente para desarrollo local
# sobre HTTP. En producción (HTTPS) debe quedar en True.
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() == "true"

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_KEY_GATEWAY = os.getenv("SECRET_KEY_GATEWAY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
JWT_EXP_DAYS = os.getenv("JWT_EXP_DAYS")
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS"))

if not SECRET_KEY_GATEWAY:
    raise RuntimeError("SECRET_KEY_GATEWAY no está configurada en el archivo .env")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY no está configurada en el archivo .env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from utils.insertLog import insert_auditoria
from utils.emailUtil import sendEmail
from utils.passwords import hash_password, verify_password, verify_password_async
from utils.redis_session import get_redis_client
from utils.rate_limiter import RateLimiter, LoginThrottler
from utils.verify_token import verify_gateway_token

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
    db: AsyncSession = Depends(get_db_managed)
):
    email = data.email.lower()
    password = data.password
    remember = data.remember
    ip_address = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    block_status = await asyncio.to_thread(LoginThrottler.check_login_block, f"{email}:{ip_address}")
    if block_status["blocked"]:
        retry_after = block_status["retry_after"] - int(time.time())
        logger.warning(f"Login bloqueado para {email[:3]}***@{email.split('@')[1]} desde {ip_address}")
        raise HTTPException(
            status_code=429,
            detail=f"Cuenta temporalmente bloqueada. Intente en {retry_after // 60} minutos.",
            headers={"Retry-After": str(retry_after)}
        )

    rate_status = await asyncio.to_thread(RateLimiter.check_rate_limit, ip_address, "login")
    if not rate_status["allowed"]:
        logger.warning(f"Rate limit excedido para IP {ip_address}")
        raise HTTPException(
            status_code=429,
            detail=f"Demasiadas solicitudes. Intente en {rate_status['retry_after']} segundos.",
            headers={"Retry-After": str(rate_status["retry_after"])}
        )

    stmt = select(
        Usuario.id,
        Usuario.rol_id,
        Usuario.hash_contrasena,
        Usuario.activo,
        Usuario.numero_documento
    ).where(Usuario.correo == email)

    result = await db.execute(stmt)
    user = result.first()

    if user is None:
        await asyncio.to_thread(LoginThrottler.record_failed_login, f"{email}:{ip_address}")
        logger.info(f"Login fallido: usuario no existe - {email[:3]}***@{email.split('@')[1]}")
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not user.activo:
        logger.info(f"Login fallido: usuario inactivo - {email[:3]}***@{email.split('@')[1]}")
        raise HTTPException(status_code=403, detail="Usuario inactivo")

    password_valid = await verify_password_async(password, user.hash_contrasena)
    if not password_valid:
        throttle_status = await asyncio.to_thread(LoginThrottler.record_failed_login, f"{email}:{ip_address}")
        logger.warning(f"Login fallido: contraseña incorrecta - {email[:3]}***@{email.split('@')[1]} - Intento #{throttle_status['attempts']}")

        if throttle_status["blocked"]:
            retry_minutes = throttle_status["block_duration"] // 60
            raise HTTPException(
                status_code=429,
                detail=f"Cuenta bloqueada por {retry_minutes} minutos.",
                headers={"Retry-After": str(throttle_status["block_duration"])}
            )

        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    token_jti = str(uuid.uuid4())
    ttl_days = int(JWT_EXP_DAYS) if remember else 1
    ttl_seconds = int(timedelta(days=ttl_days).total_seconds())

    token_data = {
        "sub": str(user.id),
        "rol_id": user.rol_id,
        "jti": token_jti,
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl_seconds
    }

    token = jwe.encrypt(
        plaintext=json.dumps(token_data).encode('utf-8'),
        key=SECRET_KEY_GATEWAY,
        algorithm='dir',
        encryption='A256GCM'
    ).decode('utf-8')

    # Sesión única por usuario: el jti guardado invalida cualquier token previo.
    r = get_redis_client()
    if r is None:
        logger.warning("Redis no disponible, sesión no guardada")
        raise HTTPException(status_code=503, detail="Servicio de autenticación temporalmente no disponible")

    await r.set(f"session:user:{user.id}", token_jti, ex=ttl_seconds)

    await asyncio.to_thread(LoginThrottler.reset_failed_logins, f"{email}:{ip_address}")
    logger.info(f"Login exitoso: {email[:3]}***@{email.split('@')[1]} desde {ip_address}")

    await insert_auditoria(
        db=db,
        usuario_id=user.id,
        tipo_evento="LOGIN",
        resultado="EXITOSO",
        detalle=f"Inicio de sesión desde {ip_address}",
        ip_address=ip_address,
        user_agent=user_agent,
    )
    await db.commit()

    response = JSONResponse({"ok": True}, 200)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="strict",
        secure=COOKIE_SECURE,
        max_age=ttl_seconds if remember else None
    )
    return response

@router.post("/recovery")
async def validar_correo(
    data: RecuperarRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    email = data.email

    stmt = select(
        Usuario.id,
        Usuario.primer_nombre,
        Usuario.primer_apellido,
        Usuario.numero_documento
    ).where(Usuario.correo == email)
    result = await db.execute(stmt)
    user_data = result.first()

    if user_data is None:
        await asyncio.sleep(0.3)
        return JSONResponse(
            content={"ok": True, "message": "Si el correo está registrado, recibirás un mensaje para continuar"},
            status_code=200
        )

    user_id = user_data[0]
    user_name = f"{user_data[1]} {user_data[2]}"
    numero_documento = user_data[3]

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

    caracteres = string.ascii_uppercase + string.digits
    code = ''.join(random.choices(caracteres, k=5))

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

    stmt = select(CodigoRecuperacion.id).where(
        CodigoRecuperacion.usuario_id == user_id
    )
    code_id = await db.scalar(stmt)

    datos_nuevos = {
        "correo": email,
        "usuario_id": user_id,
        "fecha_solicitud": datetime.now(ZoneInfo("America/Bogota")).isoformat(),
        "expiracion_minutos": 10
    }

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=user_id,
        tipo_evento="RECUPERACION_CONTRASENA",
        resultado="EXITOSO",
        detalle=f"Solicitud de código de recuperación para {email} - {user_name}",
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

@router.post("/recovery-code")
async def validar_code_de_recuperacion(
    data: RecuperarRequest,
    db: AsyncSession = Depends(get_db_managed)
):
    email = data.email
    code = data.code

    stmt_user = select(
        Usuario.id,
        Usuario.primer_nombre,
        Usuario.primer_apellido,
        Usuario.numero_documento
    ).where(Usuario.correo == email)
    result = await db.execute(stmt_user)
    user_data = result.first()

    if not user_data:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user_id = user_data[0]
    user_name = f"{user_data[1]} {user_data[2]}"
    numero_documento = user_data[3]

    stmr = select(
        CodigoRecuperacion.codigo,
        CodigoRecuperacion.intentos_fallidos
    ).where(and_(
        CodigoRecuperacion.usuario_id == user_id,
        CodigoRecuperacion.fecha_expiracion > datetime.now(ZoneInfo("America/Bogota"))
    ))
    result = await db.execute(stmr)
    result = result.first()

    if not result:
        raise HTTPException(status_code=400, detail="Código inválido o expirado")

    if result.intentos_fallidos >= 5:
        await db.execute(delete(CodigoRecuperacion).where(CodigoRecuperacion.usuario_id == user_id))
        await db.commit()
        raise HTTPException(status_code=429, detail="Demasiados intentos fallidos. Solicita un nuevo código.")

    if verify_password(code, result[0]):

        # El código es de un solo uso: se borra apenas se valida.
        stmr = delete(CodigoRecuperacion).where(
            and_(
                CodigoRecuperacion.codigo == result[0],
                CodigoRecuperacion.usuario_id == user_id
            )
        )
        await db.execute(stmr)

        mayuscula = random.choice(string.ascii_uppercase)
        numeros = random.choices(string.digits, k=2)
        simbolo = random.choice("!@#$%^&*()-_=+?¿¡[]{}<>")

        restantes = 10 - (1 + 2 + 1)
        otros = random.choices(string.ascii_letters + string.digits, k=restantes)

        cont_list = list(mayuscula + "".join(numeros) + simbolo + "".join(otros))
        random.shuffle(cont_list)
        cont = "".join(cont_list)

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

        stmt = update(Usuario).where(Usuario.correo == email).values(hash_contrasena=hash_password(cont))
        await db.execute(stmt)

        datos_nuevos = {
            "correo": email,
            "usuario_id": user_id,
            "fecha_recuperacion": datetime.now(ZoneInfo("America/Bogota")).isoformat(),
            "password_temporal_enviado": True
        }

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tipo_evento="RECUPERACION_CONTRASENA",
            resultado="EXITOSO",
            detalle=f"Recuperación de contraseña exitosa para {email} - {user_name}",
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

    await db.execute(
        update(CodigoRecuperacion)
        .where(CodigoRecuperacion.usuario_id == user_id)
        .values(intentos_fallidos=CodigoRecuperacion.intentos_fallidos + 1)
    )
    await db.commit()
    await insert_auditoria(
        db=db,
        usuario_id=user_id,
        tipo_evento="RECUPERACION_CONTRASENA",
        resultado="FALLIDO",
        detalle=f"Código inválido o expirado para {email} - {user_name}",
    )
    await db.commit()
    raise HTTPException(status_code=401, detail="Código inválido o expirado")

@router.get("/me")
async def validar_token(
    request: Request,
    db: AsyncSession = Depends(get_db_managed)
):
    # Mantiene su propio try/except: cualquier error inesperado en la validación
    # del token debe responder 401 (credenciales inválidas), no el 500 genérico
    # de get_db_managed.
    try:
        token_data = verify_gateway_token(request)
        user_id = token_data["user_id"]

        stmt = select(
            Usuario.primer_nombre,
            Usuario.segundo_nombre,
            Usuario.primer_apellido,
            Usuario.segundo_apellido,
            Usuario.correo,
            Usuario.numero_documento,
            Rol.nombre.label("rol_nombre")
        ).join(
            Rol, Rol.id == Usuario.rol_id, isouter=True
        ).where(Usuario.id == user_id)

        result = await db.execute(stmt)
        user = result.first()

        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        stmt = select(Permiso.nombre, Permiso.menu_path).join(
            RolPermiso, RolPermiso.permiso_id == Permiso.id
        ).where(RolPermiso.rol_id == token_data["rol_id"])

        result = await db.execute(stmt)
        permisos = [
            {"name": row[0], "path": row[1]} for row in result.fetchall()
        ]

        return JSONResponse({
            "ok": True,
            "usuario": {
                "user_id": user_id,
                "primer_nombre": user[0],
                "segundo_nombre": user[1] or "",
                "primer_apellido": user[2],
                "segundo_apellido": user[3] or "",
                "correo": user[4],
                "permisos": permisos,
            }
        }, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en /me: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

@router.post("/logout")
async def cerrar_sesion(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_managed)
):
    # Mantiene su propio try/except: el logout siempre debe responder ok:True y
    # borrar la cookie, incluso si falla el procesamiento del token o la sesión.
    try:
        token = request.cookies.get("access_token")

        if token:
            try:
                payload = json.loads(
                    jwe.decrypt(token, SECRET_KEY_GATEWAY).decode('utf-8')
                )

                user_id = int(payload.get("sub"))
                if not user_id:
                    return JSONResponse({"ok": False, "reason": "Token inválido"}, status_code=400)

                # Solo se borra la sesión si el token presentado es el activo:
                # un logout con token obsoleto no debe cerrar la sesión vigente.
                r = get_redis_client()
                if not r:
                    logger.warning("Redis no disponible, no se pudo eliminar sesión en logout")
                else:
                    stored_jti = await r.get(f"session:user:{user_id}")
                    if stored_jti == payload.get("jti"):
                        await r.delete(f"session:user:{user_id}")
                    else:
                        logger.info(f"Logout con token obsoleto para usuario {user_id} - sesión activa no afectada")

                await insert_auditoria(
                    db=db,
                    usuario_id=user_id,
                    tipo_evento="LOGOUT",
                    resultado="EXITOSO",
                    detalle=f"Cierre de sesión desde {request.client.host if request.client else 'unknown'}",
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent"),
                )
                await db.commit()

            except Exception as e:
                logger.warning(f"Error procesando logout: {e}")

        response.delete_cookie(
            key="access_token",
            path="/",
            httponly=True,
            samesite="strict",
            secure=COOKIE_SECURE)

        return {"ok": True}

    except Exception as e:
        logger.error(f"Error durante logout: {e}")
        response.delete_cookie(
            key="access_token",
            path="/",
            httponly=True,
            samesite="strict",
            secure=COOKIE_SECURE)
        return {"ok": True}
