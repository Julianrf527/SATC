from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists, insert, update, and_, or_, func
from pydantic import BaseModel, EmailStr, validator
from typing import List
from passlib.hash import bcrypt
from utils.passwords import hash_password, verify_password
from utils import emailUtil
from datetime import datetime
from dotenv import load_dotenv
import string
import random
import logging
import os

#----- DB -----

from db.deps import get_db
from db.models.usuario import Usuario
from db.models.rol_permiso import RolPermiso
from db.models.permiso import Permiso
from db.models.rol import Rol
from db.models.auditoria import Auditoria

router = APIRouter()
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
PERMISO_USER = os.getenv("PERMISO_USER")
GESTION_USER = os.getenv("GESTION_USER")
USER_LOG = os.getenv("USER_LOG")


# ---------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- MODELOS ----------

from pydantic import BaseModel, EmailStr, validator

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

class RecuperarRequest(BaseModel):
    email: EmailStr 
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

class UserBatchRequest(BaseModel):
    user_ids: List[int]

class UserBatchResponse(BaseModel):
    id: int
    nombre: str
    correo: str

#----------- FUNCIONES ------------

from utils.verify_gateway_token import verify_gateway_token
from utils.insertLog import insert_auditoria
from utils.verify_token_service import verify_service_jwt

# ---------- ENDPOINTS ----------

@router.post("/register")
async def registrar_usuario(
    request: Request,
    data: User,
    db: AsyncSession = Depends(get_db),
):
    try:
        # Verificar permisos
        user_id = verify_gateway_token(request)

        stmt = (
            select(1)
            .select_from(RolPermiso)
            .join(Permiso, Permiso.id == RolPermiso.permiso_id)
            .join(Usuario, Usuario.rol_id == RolPermiso.rol_id)
            .where(
                Usuario.numero_documento == user_id,
                Permiso.nombre == PERMISO_USER
            )
            .limit(1)
        )

        tiene_permiso = await db.scalar(stmt)

        if not tiene_permiso:
            raise HTTPException(status_code=403, detail="No cuenta con permisos")

        # Capitalizar nombres (por si acaso no se hizo en frontend)
        def capitalize_name(name: str) -> str:
            return name.strip().capitalize() if name else ""

        first_name = capitalize_name(data.first_name)
        middle_name = capitalize_name(data.middle_name) if data.middle_name else ""
        lastname = capitalize_name(data.lastname)
        second_lastname = capitalize_name(data.second_lastname) if data.second_lastname else ""
        
        # Construir nombre completo para auditoría
        full_name_parts = [first_name]
        if middle_name:
            full_name_parts.append(middle_name)
        full_name_parts.append(lastname)
        if second_lastname:
            full_name_parts.append(second_lastname)
        full_name = " ".join(full_name_parts)

        document = data.document
        email = data.email.lower()  # Asegurar minúsculas
        rol = data.rol

        # Generar contraseña
        mayuscula = random.choice(string.ascii_uppercase)
        numeros = random.choices(string.digits, k=2)
        simbolo = random.choice("!@#$%^&*()-_=+?¿¡[]{}<>")
        
        restantes = 10 - (1 + 2 + 1)
        otros = random.choices(string.ascii_letters + string.digits, k=restantes)

        cont_list = list(mayuscula + "".join(numeros) + simbolo + "".join(otros))
        random.shuffle(cont_list)
        password_plain = "".join(cont_list)
        password_hashed = hash_password(password_plain)

        # Verificar duplicados
        exist_doc = await db.execute(select(exists().where(Usuario.numero_documento == document)))
        if exist_doc.scalar():
            raise HTTPException(status_code=409, detail="El número de documento ya está registrado")

        exist_email = await db.execute(select(exists().where(Usuario.correo == email)))
        if exist_email.scalar():
            raise HTTPException(status_code=409, detail="El correo electrónico ya está registrado")

        # Verificar que el rol existe
        rol_exists = await db.execute(select(exists().where(Rol.id == rol)))
        if not rol_exists.scalar():
            raise HTTPException(status_code=404, detail="El rol seleccionado no existe")

        # Insertar usuario
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

        # Datos para auditoría
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

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tabla_afectada="usuario",
            tipo_operacion="INSERT",
            descripcion=f"Creación de usuario {full_name} con documento {document}",
            id_registro=str(document),
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit antes de enviar email
        await db.commit()

        # Enviar correo con contraseña
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
            # Si falla el email, loguear pero no fallar el registro
            logger.warning(f"No se pudo enviar el email de bienvenida a {email}: {str(e)}")

        return JSONResponse({"ok": True, "message": "Usuario registrado exitosamente"}, status_code=201)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en registro de usuario: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/all")
async def obtener_usuarios(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)

        stmt = (
            select(1)
            .select_from(RolPermiso)
            .join(Permiso, Permiso.id == RolPermiso.permiso_id)
            .join(Usuario, Usuario.rol_id == RolPermiso.rol_id)
            .where(
                Usuario.numero_documento == user_id,
                Permiso.nombre == GESTION_USER
            )
            .limit(1)
        )

        tiene_permiso = await db.scalar(stmt)

        if not tiene_permiso:
            raise HTTPException(status_code=403, detail="No cuenta con permisos")
        
        stmr = select(
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
                "id": user.numero_documento,
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

    except Exception as e:
        logger.error(f"Error en el servidor al cargar los usuarios: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/toggleState/{document}")
async def actualizar_estado(
    request: Request,
    document: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)

        stmt = (
            select(1)
            .select_from(RolPermiso)
            .join(Permiso, Permiso.id == RolPermiso.permiso_id)
            .join(Usuario, Usuario.rol_id == RolPermiso.rol_id)
            .where(
                Usuario.numero_documento == user_id,
                Permiso.nombre == GESTION_USER
            )
            .limit(1)
        )

        tiene_permiso = await db.scalar(stmt)

        if not tiene_permiso:
            raise HTTPException(status_code=403, detail="No cuenta con permisos")

        stmr = select(Usuario.activo).where(Usuario.numero_documento == document)
        result = await db.execute(stmr)
        current_state = result.scalar()

        if current_state is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        datos_anteriores = {
            "numero_documento": document,
            "activo": current_state
        }

        stmr = update(Usuario).where(Usuario.numero_documento == document).values(activo=not current_state)
        await db.execute(stmr)

        datos_nuevos = {
            "numero_documento": document,
            "activo": not current_state
        }

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tabla_afectada="usuario",
            tipo_operacion="UPDATE",
            descripcion=f"Cambio de estado de usuario {document}: {current_state} → {not current_state}",
            id_registro=str(document),
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

        return JSONResponse({"ok": True}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor al cambiar estado: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/toggleRol/{document}/{rol_id}")
async def actualizar_rol(
    request:Request,
    document: int,
    rol_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)

        stmt = (
            select(1)
            .select_from(RolPermiso)
            .join(Permiso, Permiso.id == RolPermiso.permiso_id)
            .join(Usuario, Usuario.rol_id == RolPermiso.rol_id)
            .where(
                Usuario.numero_documento == user_id,
                Permiso.nombre == GESTION_USER
            )
            .limit(1)
        )

        tiene_permiso = await db.scalar(stmt)

        if not tiene_permiso:
            raise HTTPException(status_code=403, detail="No cuenta con permisos")

        stmr = select(Usuario).where(Usuario.numero_documento == document)
        result = await db.execute(stmr)
        usuario = result.scalar_one_or_none()
        
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        datos_anteriores = {
            "numero_documento": document,
            "rol_id": usuario.rol_id
        }

        stmr = update(Usuario).where(Usuario.numero_documento == document).values(rol_id=rol_id)
        await db.execute(stmr)

        datos_nuevos = {
            "numero_documento": document,
            "rol_id": rol_id
        }

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tabla_afectada="usuario",
            tipo_operacion="UPDATE",
            descripcion=f"Cambio de rol de usuario {document}: {usuario.rol_id} → {rol_id}",
            id_registro=str(document),
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

        return JSONResponse({"ok": True}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor al cambiar rol: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/password-resets")
async def cambiar_contrasena(
    request: Request,
    data: RecuperarRequest, 
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)

        email = data.email
        new_password = data.new_password

        stmr = ( 
                update(Usuario).where(
                Usuario.numero_documento == user_id, 
                Usuario.correo == email
            ).values(
                hash_contrasena=hash_password(new_password)
            ).returning(Usuario.numero_documento)
        )

        new_user_id = await db.scalar(stmr)
        
        if user_id != new_user_id:
            raise HTTPException(status_code=403, detail="No cuenta con permisos")

        datos_nuevos = {
            "numero_documento": new_user_id,
            "accion": "cambio_contrasena"
        }

        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tabla_afectada="usuario",
            tipo_operacion="UPDATE",
            descripcion=f"Cambio de contraseña del usuario {user_id}",
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

        return JSONResponse(content={"ok": True, "message": "Contraseña actualizada"}, status_code=200)
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor al recuperar contraseña: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update-user")
async def update_user(
    request: Request,
    data: UsuarioRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)

        # Capitalizar nombres
        def capitalize_name(name: str) -> str:
            return name.strip().capitalize() if name else ""

        first_name = capitalize_name(data.first_name)
        middle_name = capitalize_name(data.middle_name) if data.middle_name else ""
        lastname = capitalize_name(data.lastname)
        second_lastname = capitalize_name(data.second_lastname) if data.second_lastname else ""
        nuevo_correo = data.correo.lower()

        # Construir nombre completo
        full_name_parts = [first_name]
        if middle_name:
            full_name_parts.append(middle_name)
        full_name_parts.append(lastname)
        if second_lastname:
            full_name_parts.append(second_lastname)
        full_name = " ".join(full_name_parts)

        # Obtener usuario actual
        usuario = await db.scalar(
            select(Usuario).where(Usuario.numero_documento == user_id)
        )
        if not usuario:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # Guardar datos anteriores para auditoría
        datos_anteriores = {
            "numero_documento": user_id,
            "primer_nombre": usuario.primer_nombre,
            "segundo_nombre": usuario.segundo_nombre,
            "primer_apellido": usuario.primer_apellido,
            "segundo_apellido": usuario.segundo_apellido,
            "correo": usuario.correo
        }

        # Verificar que el correo no esté en uso por otro usuario
        existe_correo = await db.scalar(
            select(Usuario).where(
                Usuario.correo == nuevo_correo,
                Usuario.numero_documento != user_id
            )
        )
        if existe_correo:
            raise HTTPException(
                status_code=400, 
                detail="El correo ya está en uso por otro usuario"
            )

        # Actualizar usuario
        stmt = (
            update(Usuario)
            .where(Usuario.numero_documento == user_id)
            .values(
                primer_nombre=first_name,
                segundo_nombre=middle_name if middle_name else None,
                primer_apellido=lastname,
                segundo_apellido=second_lastname if second_lastname else None,
                correo=nuevo_correo
            )
        )
        await db.execute(stmt)

        # Datos nuevos para auditoría
        datos_nuevos = {
            "numero_documento": user_id,
            "nombre_completo": full_name,
            "primer_nombre": first_name,
            "segundo_nombre": middle_name if middle_name else None,
            "primer_apellido": lastname,
            "segundo_apellido": second_lastname if second_lastname else None,
            "correo": nuevo_correo
        }

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tabla_afectada="usuario",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de datos del usuario {full_name}",
            id_registro=str(user_id),
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

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor al actualizar usuario: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
    
# Endpoint de Auditoría
@router.get("/log")
async def obtener_auditoria(
    request: Request,
    usuario_id: int = Query(None, description="ID del usuario (número de documento)"),
    nombre_usuario: str = Query(None, description="Nombre del usuario (busca en nombres y apellidos)"),
    tabla_afectada: str = Query(None, description="Tabla afectada"),
    tipo_operacion: str = Query(None, description="Tipo de operación: INSERT, UPDATE, DELETE"),
    id_registro: str = Query(None, description="ID del registro afectado"),
    fecha_inicio: str = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: str = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtiene los registros de auditoría general filtrados por diferentes criterios.
    Solo accesible para usuarios con el permiso USER_LOG.
    """
    try:
        # Verificar permisos
        user_id = verify_gateway_token(request)

        stmt = (
            select(1)
            .select_from(RolPermiso)
            .join(Permiso, Permiso.id == RolPermiso.permiso_id)
            .join(Usuario, Usuario.rol_id == RolPermiso.rol_id)
            .where(
                Usuario.numero_documento == user_id,
                Permiso.nombre == USER_LOG
            )
            .limit(1)
        )

        tiene_permiso = await db.scalar(stmt)

        if not tiene_permiso:
            raise HTTPException(status_code=403, detail="No cuenta con permisos")
        
        # Consulta base con joins para obtener información del usuario
        query = select(
            Auditoria.id,
            Auditoria.usuario_id,
            Auditoria.tabla_afectada,
            Auditoria.tipo_operacion,
            Auditoria.descripcion,
            Auditoria.id_registro,
            Auditoria.fecha,
            Auditoria.datos_anteriores,
            Auditoria.datos_nuevos,
            Usuario.primer_nombre,
            Usuario.segundo_nombre,
            Usuario.primer_apellido,
            Usuario.segundo_apellido,
            Usuario.correo.label("usuario_correo")
        ).join(
            Usuario, Auditoria.usuario_id == Usuario.numero_documento, isouter=True
        )

        # Aplicar filtros
        conditions = []
        
        if usuario_id:
            conditions.append(Auditoria.usuario_id == usuario_id)
        
        # Filtro por nombre (busca en todos los campos de nombre y apellido)
        if nombre_usuario:
            nombre_lower = f"%{nombre_usuario.lower()}%"
            nombre_conditions = or_(
                func.lower(Usuario.primer_nombre).like(nombre_lower),
                func.lower(Usuario.segundo_nombre).like(nombre_lower),
                func.lower(Usuario.primer_apellido).like(nombre_lower),
                func.lower(Usuario.segundo_apellido).like(nombre_lower),
                func.lower(func.concat(Usuario.primer_nombre, ' ', Usuario.primer_apellido)).like(nombre_lower),
                func.lower(func.concat(Usuario.primer_nombre, ' ', Usuario.segundo_nombre, ' ', Usuario.primer_apellido, ' ', Usuario.segundo_apellido)).like(nombre_lower)
            )
            conditions.append(nombre_conditions)
        
        if tabla_afectada:
            conditions.append(Auditoria.tabla_afectada.ilike(f"%{tabla_afectada}%"))
        
        if tipo_operacion:
            conditions.append(Auditoria.tipo_operacion == tipo_operacion.upper())
        
        if id_registro:
            conditions.append(Auditoria.id_registro.ilike(f"%{id_registro}%"))
        
        if fecha_inicio:
            try:
                fecha_inicio_date = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                conditions.append(Auditoria.fecha >= fecha_inicio_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Formato de fecha_inicio inválido. Use YYYY-MM-DD"
                )
        
        if fecha_fin:
            try:
                fecha_fin_date = datetime.strptime(fecha_fin, "%Y-%m-%d")
                # Incluir todo el día final
                fecha_fin_date = fecha_fin_date.replace(hour=23, minute=59, second=59)
                conditions.append(Auditoria.fecha <= fecha_fin_date)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Formato de fecha_fin inválido. Use YYYY-MM-DD"
                )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Contar total de registros
        count_query = select(func.count()).select_from(Auditoria)
        if conditions:
            # Para el count, necesitamos incluir el join si hay filtro de nombre
            if nombre_usuario:
                count_query = count_query.join(
                    Usuario, Auditoria.usuario_id == Usuario.numero_documento, isouter=True
                )
            count_query = count_query.where(and_(*conditions))
        
        total_result = await db.execute(count_query)
        total_records = total_result.scalar()
        
        # Ordenar por fecha descendente y aplicar paginación
        query = query.order_by(Auditoria.fecha.desc()).limit(limit).offset(offset)
        
        result = await db.execute(query)
        logs = result.fetchall()
        
        # Formatear respuesta con nombre completo
        logs_data = []
        for log in logs:
            # Construir nombre completo
            nombre_partes = [
                log.primer_nombre,
                log.segundo_nombre,
                log.primer_apellido,
                log.segundo_apellido
            ]
            nombre_completo = " ".join([p for p in nombre_partes if p])
            
            logs_data.append({
                "id": log.id,
                "usuario_id": log.usuario_id,
                "usuario_nombre": nombre_completo or "Usuario Desconocido",
                "usuario_correo": log.usuario_correo,
                "tabla_afectada": log.tabla_afectada,
                "tipo_operacion": log.tipo_operacion,
                "descripcion": log.descripcion,
                "id_registro": log.id_registro,
                "fecha": log.fecha.isoformat() if log.fecha else None,
                "datos_anteriores": log.datos_anteriores,
                "datos_nuevos": log.datos_nuevos
            })
        
        return JSONResponse(
            content={
                "ok": True,
                "msg": f"Se encontraron {len(logs_data)} registros de auditoría",
                "data": logs_data,
                "pagination": {
                    "total": total_records,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total_records
                }
            },
            status_code=200
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo registros de auditoría: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error al obtener registros de auditoría"
        )

@router.post("/batch")
async def obtener_usuarios_batch(
    request: Request,
    data: UserBatchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtiene información básica de múltiples usuarios por sus IDs.
    SOLO para comunicación entre servicios internos.

    """
    try:
        # Verificar que sea una llamada de servicio a servicio
        service_name = verify_service_jwt(request)
        
        if not data.user_ids:
            return JSONResponse(
                content={"ok": True, "data": []},
                status_code=200
            )
        
        if len(data.user_ids) > 100:
            raise HTTPException(
                status_code=400,
                detail="Máximo 100 usuarios por solicitud"
            )
        
        stmt = select(
            Usuario.numero_documento,
            Usuario.primer_nombre,
            Usuario.segundo_nombre,
            Usuario.primer_apellido,
            Usuario.segundo_apellido,
            Usuario.correo
        ).where(Usuario.numero_documento.in_(data.user_ids))
        
        result = await db.execute(stmt)
        users = result.fetchall()
        
        users_data = []
        for user in users:
            nombre_parts = [user.primer_nombre]
            if user.segundo_nombre:
                nombre_parts.append(user.segundo_nombre)
            nombre_parts.append(user.primer_apellido)
            if user.segundo_apellido:
                nombre_parts.append(user.segundo_apellido)
            
            nombre_completo = " ".join(nombre_parts)
            
            users_data.append({
                "id": user.numero_documento,
                "nombre": nombre_completo,
                "correo": user.correo
            })
        
        return JSONResponse(
            content={"ok": True, "data": users_data},
            status_code=200
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo usuarios batch: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error al obtener información de usuarios"
        )

@router.get("/permission/{permission_name}")
async def obtener_usuarios_por_permiso(
    request: Request,
    permission_name: str,
    db: AsyncSession = Depends(get_db)
):  
    """
    Obtiene información básica de múltiples usuarios por permiso.
    SOLO para comunicación entre servicios internos.
    """

    try:
        service_name = verify_service_jwt(request)
        
        # 1. Buscar permiso
        permiso_id = (
            await db.execute(
                select(Permiso.id).where(Permiso.nombre == permission_name)
            )
        ).scalar_one_or_none()

        if not permiso_id:
            raise HTTPException(status_code=404, detail="Permiso no encontrado")

        # 2. Traer todos los usuarios con ese permiso (UNA sola consulta)
        result = await db.execute(
            select(
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

        users_data = []
        for r in rows:

            nombre_completo = " ".join(
                part for part in [
                    r.primer_nombre,
                    r.segundo_nombre,
                    r.primer_apellido,
                    r.segundo_apellido
                ] if part
            )

            users_data.append({
                "id": r.numero_documento,
                "nombre": nombre_completo,
                "correo": r.correo
            })

        return JSONResponse(
            content={"ok": True, "data": users_data},
            status_code=200
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo usuarios batch: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error al obtener información de usuarios"
        )