from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, insert
from pydantic import BaseModel
import logging
import os

#----- DB -----

from db.deps import get_db
from db.models.rol import Rol
from db.models.permiso import Permiso
from db.models.rol_permiso import RolPermiso
from db.models.usuario import Usuario
from core.permissions import Permisos

router = APIRouter()
SECRET_KEY = os.getenv("SECRET_KEY")
PERMISO_ROL = Permisos.PERMISO_ROL

# ---------- LOGGER ------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- MODELOS ----------
class RolCreate(BaseModel):
    name: str
    permission: list[int]

class PerCreate(BaseModel):
    name:str
    menu_path: str

class Permission(BaseModel):
    name: str
    user_id: int

#----------- FUNCIONES ------------

from utils.insertLog import insert_auditoria
from utils.verify_token import verify_gateway_token
from utils.verify_permission import verify_permission
from utils.permission_crud import get_role_permissions, get_user_permission_names, get_user_permission_avaliable, get_user_rol_avaliable, get_permissions_by_rol_id

# ---------- ENDPOINTS ----------

@router.get("/all")
async def cargar_roles(
    request: Request,
    db: AsyncSession = Depends(get_db),
    ):
    try:
        token_data = verify_gateway_token(request)
        verify_permission(token_data, PERMISO_ROL)

        # Obtener permisos actuales del usuario desde BD
        # (el token puede estar desactualizado si se crearon nuevos permisos)
        user_permissions = await get_permissions_by_rol_id(token_data["rol_id"], db)
        user_permission_names = {p["name"] for p in user_permissions}

        # Filtrar roles que el usuario puede gestionar
        data = await get_user_rol_avaliable(user_permission_names, db)

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)

    except Exception as e:
        logger.error(f"Error en /rol: {e}")
        raise HTTPException(status_code=500, detail="Error al cargar los roles.")

@router.get("/permissions")
async def cargar_permisos(
    request: Request,
    db: AsyncSession = Depends(get_db),
    ):
    try:
        token_data = verify_gateway_token(request)
        logger.info(f"Token data: {token_data}")
        verify_permission(token_data, PERMISO_ROL)

        # FILTRADO DE SEGURIDAD: Consultar permisos del rol desde la BD en tiempo real
        # (no usar token_data["permisos"] ya que está desactualizado si se crean nuevos permisos)
        permission = await get_permissions_by_rol_id(token_data["rol_id"], db)

        return JSONResponse(content={"ok": True, "data": permission}, status_code=200)

    except Exception as e:
        logger.error(f"Error en /permissions: {e}")
        raise HTTPException(status_code=500, detail="Error al cargar los permisos.")

@router.get("/role-permissions")
async def cargar_permiso_y_roles(
    request: Request,
    db: AsyncSession = Depends(get_db)
    ):
    try:
        token_data = verify_gateway_token(request)
        verify_permission(token_data, PERMISO_ROL)

        # FILTRADO DE SEGURIDAD: Solo mostrar roles que el usuario puede gestionar
        data = await get_user_rol_avaliable(token_data["permisos"], db)
        logger.info(f"Permisos permitidos: {data}")

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)
    except Exception as e:
        logger.error(f"Error en /rol-permiso: {e}")
        raise HTTPException(status_code=500, detail="Error al cargar los roles y permisos.")

@router.post("/add")
async def agregar_rol(
    request: Request,
    rol: RolCreate,
    db: AsyncSession = Depends(get_db),
    ):
    try:
        token_data = verify_gateway_token(request)
        verify_permission(token_data, PERMISO_ROL)

        # VALIDACIÓN DE ESCALADA DE PRIVILEGIOS: El usuario solo puede asignar permisos que él mismo posee
        requested_permission_names = await get_user_permission_names(rol.permission, db)

        if len(requested_permission_names - set(token_data["permisos"])) > 0:
            raise HTTPException(
                status_code=403,
                detail=f"No puede asignar permisos que no posee."
            )

        # Verificar si el rol ya existe
        stmr = select(Rol).where(Rol.nombre == rol.name)
        result = await db.execute(stmr)
        existing_rol = result.scalar_one_or_none()
        if existing_rol:
            logger.warning(f"[agregar_rol] El rol '{rol.name}' ya existe")
            raise HTTPException(status_code=400, detail="El rol ya existe")

        # Crear nuevo rol
        stmt = (
            insert(Rol)
            .values(nombre=rol.name)
            .returning(Rol.id)
        )

        result = await db.execute(stmt)
        new_rol_id = result.scalar()
        logger.info(f"[agregar_rol] Nuevo rol creado con ID: {new_rol_id}")

        # Asignar permisos al nuevo rol
        for permiso_id in rol.permission:
            logger.info(f"[agregar_rol] Asignando permiso {permiso_id} al rol {new_rol_id}")
            rp = RolPermiso(rol_id=new_rol_id, permiso_id=permiso_id)
            db.add(rp)

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": new_rol_id,
            "nombre": rol.name,
            "permisos": rol.permission
        }

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=token_data["user_id"],
            documento_usuario=token_data["documento"],
            nombre_usuario=token_data["nombre"],
            tipo_evento="CREACION_ROL",
            resultado="EXITOSO",
            detalle=f"Creacion de rol ID {new_rol_id} a nombre '{rol.name}'",
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            logger.error(f"[agregar_rol] Error al guardar registro de auditoría: {audit_result}")
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        logger.info(f"[agregar_rol] Rol creado exitosamente")
        return JSONResponse(content={"ok": True}, status_code=201)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor durante delete rol: {e}")
        raise HTTPException(status_code=500, detail="Error al crear el rol.")

@router.put("/update/{rol_id}")
async def actualizar_rol(
    request: Request,
    rol_id: int,
    data: RolCreate,
    db: AsyncSession = Depends(get_db),
    ):
    try:
        token_data = verify_gateway_token(request)
        verify_permission(token_data, PERMISO_ROL)

        # VALIDACIÓN DE ESCALADA DE PRIVILEGIOS: El usuario solo puede asignar permisos que él mismo posee
        requested_permission_names = await get_user_permission_names(data.permission, db)

        if len(requested_permission_names - set(token_data["permisos"])) > 0:
            raise HTTPException(
                status_code=403,
                detail=f"No puede asignar permisos que no posee."
            )

        # Verificar si el rol existe y obtener datos anteriores
        stmr = select(Rol).where(Rol.id == rol_id)
        result = await db.execute(stmr)
        existing_rol = result.scalar_one_or_none()
        if not existing_rol:
            raise HTTPException(status_code=404, detail="El rol no existe")

        # Obtener permisos anteriores
        stmr_permisos = select(RolPermiso.permiso_id).where(RolPermiso.rol_id == rol_id)
        result_permisos = await db.execute(stmr_permisos)
        permisos_anteriores = [row[0] for row in result_permisos.fetchall()]

        datos_anteriores = {
            "id": existing_rol.id,
            "nombre": existing_rol.nombre,
            "permisos": permisos_anteriores
        }

        # Verificar duplicado de nombre
        stmr = select(Rol).where(Rol.nombre == data.name, Rol.id != rol_id)
        result = await db.execute(stmr)
        duplicate_rol = result.scalar_one_or_none()
        if duplicate_rol:
            raise HTTPException(status_code=400, detail="El nombre de rol ya está en uso")

        # Actualizar nombre del rol
        stmr = update(Rol).where(Rol.id == rol_id).values(nombre=data.name)
        await db.execute(stmr)

        # Actualizar permisos del rol
        await db.execute(delete(RolPermiso).where(RolPermiso.rol_id == rol_id))
        for permiso_id in data.permission:
            rol_permiso = RolPermiso(rol_id=rol_id, permiso_id=permiso_id)
            db.add(rol_permiso)

        datos_nuevos = {
            "id": rol_id,
            "nombre": data.name,
            "permisos": data.permission
        }

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=token_data["user_id"],
            documento_usuario=token_data["documento"],
            nombre_usuario=token_data["nombre"],
            tipo_evento="ACTUALIZACION_ROL",
            resultado="EXITOSO",
            detalle=f"Actualización de rol ID {rol_id} a nombre '{data.name}'",
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()

        return JSONResponse(content={"ok": True}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor durante update rol: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar el rol.")

@router.delete("/delete/{rol_id}")
async def eliminar_rol(
    request: Request,
    rol_id: int,
    db: AsyncSession = Depends(get_db),
    ):
    try:
        token_data = verify_gateway_token(request)
        verify_permission(token_data, PERMISO_ROL)

        # Verificar si el rol existe y obtener datos anteriores
        stmr = select(Rol).where(Rol.id == rol_id)
        result = await db.execute(stmr)
        existing_rol = result.scalar_one_or_none()
        if not existing_rol:
            raise HTTPException(status_code=404, detail="El rol no existe")

        # VALIDACIÓN DE SEGURIDAD: Verificar si el rol está asignado a algún usuario
        stmt_usuarios = select(Usuario.id).where(Usuario.rol_id == rol_id).limit(1)
        usuario_asignado = await db.scalar(stmt_usuarios)

        if usuario_asignado:
            raise HTTPException(
                status_code=400,
                detail="No se puede eliminar el rol porque está asignado a uno o más usuarios"
            )

        # Obtener permisos anteriores
        stmt = (
            select(
                Permiso.id,
                Permiso.nombre,
                Permiso.menu_path
            )
            .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
            .where(RolPermiso.rol_id == rol_id)
        )

        result = await db.execute(stmt)
        rows = result.all()

        #Verificacion
        permissions_name = set([row.nombre for row in rows])
        if len(permissions_name - set(token_data["permisos"])) > 0:
            raise HTTPException(
                status_code=403,
                detail=f"No puede eliminar un rol que tiene permisos que no posee."
            )

        data = {
            "rol_id": existing_rol.id,
            "rol_name": existing_rol.nombre,
            "permisos": [
                {
                    "id": row.id,
                    "nombre": row.nombre,
                    "menu_path": row.menu_path
                }
                for row in rows
            ]
        }

        # Eliminar permisos asociados al rol
        await db.execute(delete(RolPermiso).where(RolPermiso.rol_id == rol_id))

        # Eliminar el rol
        await db.execute(delete(Rol).where(Rol.id == rol_id))

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=token_data["user_id"],
            documento_usuario=token_data["documento"],
            nombre_usuario=token_data["nombre"],
            tipo_evento="ELIMINACION_ROL",
            resultado="EXITOSO",
            detalle=f"Eliminación de rol ID {rol_id} con nombre '{existing_rol.nombre}'",
            datos_anteriores=data
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()

        return JSONResponse(content={"ok": True}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor durante delete rol: {e}")
        raise HTTPException(status_code=500, detail="Error al eliminar el rol.")

@router.post("/permission/add")
async def agregar_permiso(
    request: Request,
    permission: PerCreate,
    db: AsyncSession = Depends(get_db)
    ):
    try:
        token_data = verify_gateway_token(request)
        verify_permission(token_data, PERMISO_ROL)
        
        stmt = select(Permiso.id).where(Permiso.nombre == permission.name)
        permiso_id = await db.scalar(stmt)

        if permiso_id:
            raise HTTPException(status_code=400, detail="El nombre de permiso ya está en uso")

        stmt = (
            insert(Permiso)
            .values(nombre = permission.name, menu_path = permission.menu_path)
            .returning(Permiso.id)
        )
        permiso_id = await db.scalar(stmt)
        #Agregar permiso al usuario que lo creo
        rp = RolPermiso(rol_id=token_data["rol_id"], permiso_id=permiso_id)
        db.add(rp)

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": permiso_id,
            "nombre": permission.name,
            "menu_path": permission.menu_path,
        }

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=token_data["user_id"],
            documento_usuario=token_data["documento"],
            nombre_usuario=token_data["nombre"],
            tipo_evento="CREACION_PERMISO",
            resultado="EXITOSO",
            detalle=f"Creacion de permioso ID {permiso_id} con nombre '{permission.name}'",
            datos_nuevos=datos_nuevos
        )
        
        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        return JSONResponse(content={"ok": True, "permiso_id": permiso_id}, status_code=201)

    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor durante create permission: {e}")
        raise HTTPException(status_code=500, detail="Error al crear el permiso.")

@router.put("/permission/update/{permiso_id}")
async def actualizar_permiso(
    request: Request,
    permiso_id: int,
    permission: PerCreate,
    db: AsyncSession = Depends(get_db)
    ):
    try:
        token_data = verify_gateway_token(request)
        verify_permission(token_data, PERMISO_ROL)

        # Verificar que el permiso existe
        stmt = select(Permiso).where(Permiso.id == permiso_id)
        permiso_existente = await db.scalar(stmt)

        if not permiso_existente:
            raise HTTPException(status_code=404, detail="Permiso no encontrado")

        if permiso_existente.nombre not in token_data["permisos"]:
            raise HTTPException(
                status_code=403,
                detail="No puede actualizar un permiso que no posee"
            )

        # Verificar que el nuevo nombre no esté en uso (excepto por el mismo permiso)
        stmt = select(Permiso.id).where(
            Permiso.nombre == permission.name,
            Permiso.id != permiso_id
        )
        nombre_en_uso = await db.scalar(stmt)

        if nombre_en_uso:
            raise HTTPException(status_code=400, detail="El nombre de permiso ya está en uso")

        # Actualizar el permiso
        stmt = (
            update(Permiso)
            .where(Permiso.id == permiso_id)
            .values(
                nombre=permission.name,
                menu_path=permission.menu_path
            )
        )
        await db.execute(stmt)

        # Guardar datos antiguos para auditoría
        datos_antiguos = {
            "id": permiso_existente.id,
            "nombre": permiso_existente.nombre,
            "menu_path": permiso_existente.menu_path,
        }

        # Preparar datos nuevos para auditoría
        datos_nuevos = {
            "id": permiso_id,
            "nombre": permission.name,
            "menu_path": permission.menu_path,
        }

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=token_data["user_id"],
            documento_usuario=token_data["documento"],
            nombre_usuario=token_data["nombre"],
            tipo_evento="ACTUALIZACION_PERMISO",
            resultado="EXITOSO",
            detalle=f"Actualización de permiso ID {permiso_id} con nombre '{permission.name}'",
            datos_anteriores=datos_antiguos,
            datos_nuevos=datos_nuevos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        return JSONResponse(content={"ok": True, "message": "Permiso actualizado correctamente"}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor durante update permission: {e}")
        raise HTTPException(status_code=500, detail="Error al actualizar el permiso.")

@router.delete("/permission/delete/{permiso_id}")
async def eliminar_permiso(
    request: Request,
    permiso_id: int,
    db: AsyncSession = Depends(get_db)
    ):
    try:
        token_data = verify_gateway_token(request)
        verify_permission(token_data, PERMISO_ROL)

        # Verificar que el permiso existe
        stmt = select(Permiso).where(Permiso.id == permiso_id)
        permiso_existente = await db.scalar(stmt)

        if not permiso_existente:
            raise HTTPException(status_code=404, detail="Permiso no encontrado")

        # Verificar que el usuario posee el permiso consultando la BD en tiempo real
        # (token_data["permisos"] puede estar desactualizado si el permiso fue creado después del login)
        user_permissions = await get_permissions_by_rol_id(token_data["rol_id"], db)
        user_permission_names = {p["name"] for p in user_permissions}

        if permiso_existente.nombre not in user_permission_names:
            raise HTTPException(
                status_code=403,
                detail="No puede eliminar un permiso que no posee."
            )

        # Contar cuántos roles tienen este permiso asignado (para el mensaje informativo)
        stmt_roles = select(RolPermiso.rol_id).where(RolPermiso.permiso_id == permiso_id)
        result_roles = await db.execute(stmt_roles)
        roles_afectados = result_roles.scalars().all()
        cantidad_roles = len(roles_afectados)

        # Eliminar el permiso de todos los roles que lo tienen asignado (cascada)
        await db.execute(delete(RolPermiso).where(RolPermiso.permiso_id == permiso_id))

        # Guardar datos antiguos para auditoría
        datos_antiguos = {
            "id": permiso_existente.id,
            "nombre": permiso_existente.nombre,
            "menu_path": permiso_existente.menu_path,
            "roles_afectados": cantidad_roles,
        }

        # Eliminar el permiso
        stmt = delete(Permiso).where(Permiso.id == permiso_id)
        await db.execute(stmt)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=token_data["user_id"],
            documento_usuario=token_data["documento"],
            nombre_usuario=token_data["nombre"],
            tipo_evento="ELIMINACION_PERMISO",
            resultado="EXITOSO",
            detalle=f"Eliminación de permiso ID {permiso_id} con nombre '{permiso_existente.nombre}'. Removido de {cantidad_roles} rol(es).",
            datos_anteriores=datos_antiguos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()

        msg = f"Permiso eliminado correctamente"
        if cantidad_roles > 0:
            msg += f" (removido de {cantidad_roles} rol(es))"

        return JSONResponse(content={"ok": True, "message": msg}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor durante delete permission: {e}")
        raise HTTPException(status_code=500, detail="Error al eliminar el permiso.")
