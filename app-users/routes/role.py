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

router = APIRouter()
SECRET_KEY = os.getenv("SECRET_KEY")
PERMISO_ROL = os.getenv("PERMISO_ROL")

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
from utils.verify_gateway_token import verify_gateway_token

async def get_user_permissions(user_id: int, db: AsyncSession) -> set[int]:
    """
    Obtiene el conjunto de IDs de permisos que posee un usuario.
    
    Args:
        user_id: Número de documento del usuario
        db: Sesión de base de datos
    
    Returns:
        set[int]: Conjunto de IDs de permisos del usuario
    """
    stmt = (
        select(Permiso.id)
        .select_from(RolPermiso)
        .join(Permiso, Permiso.id == RolPermiso.permiso_id)
        .join(Usuario, Usuario.rol_id == RolPermiso.rol_id)
        .where(Usuario.numero_documento == user_id)
    )
    
    result = await db.execute(stmt)
    permission_ids = result.scalars().all()
    
    return set(permission_ids)


async def get_role_permissions(rol_id: int, db: AsyncSession) -> set[int]:
    """
    Obtiene el conjunto de IDs de permisos que tiene un rol.
    
    Args:
        rol_id: ID del rol
        db: Sesión de base de datos
    
    Returns:
        set[int]: Conjunto de IDs de permisos del rol
    """
    stmt = (
        select(RolPermiso.permiso_id)
        .where(RolPermiso.rol_id == rol_id)
    )
    
    result = await db.execute(stmt)
    permission_ids = result.scalars().all()
    
    return set(permission_ids)

# ---------- ENDPOINTS ----------

@router.get("/all")
async def cargar_roles(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)

        stmr = select(Rol)
        result = await db.execute(stmr)
        result = result.all()

        data = [{"id": rol[0].id, "name": rol[0].nombre} for rol in result]

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)

    except Exception as e:
        logger.error(f"Error en /rol: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")

@router.get("/permissions")
async def cargar_permisos(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        user_id = verify_gateway_token(request)

        stmr = select(Permiso)
        result = await db.execute(stmr)
        result = result.all()

        data = [
            {"id": permiso[0].id, "name": permiso[0].nombre, "menu_path": permiso[0].menu_path}
            for permiso in result
        ]

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)

    except Exception as e:
        logger.error(f"Error en /permissions: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")

@router.get("/role-permissions")
async def cargar_permiso_y_roles(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = verify_gateway_token(request)

        stmr = select(Rol.id, Rol.nombre, RolPermiso.permiso_id).join(RolPermiso, Rol.id == RolPermiso.rol_id)
        result = await db.execute(stmr)
        result = result.all()

        data = {}
        for rol_id, rol_nombre, permiso_id in result:
            if rol_id not in data:
                data[rol_id] = {"id": rol_id, "name": rol_nombre, "permission": []}
            data[rol_id]["permission"].append(permiso_id)
        data = list(data.values())

        return JSONResponse(content={"ok": True, "data": data}, status_code=200)
    except Exception as e:
        logger.error(f"Error en /rol-permiso: {e}")
        raise HTTPException(status_code=500, detail="Error en el servidor")

@router.post("/add/")
async def agregar_rol(
    request: Request,
    rol: RolCreate,
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
                Permiso.nombre == PERMISO_ROL
            )
            .limit(1)
        )

        tiene_permiso = await db.scalar(stmt)

        if not tiene_permiso:
            raise HTTPException(status_code=403, detail="No cuenta con permisos")

        # VALIDACIÓN DE ESCALADA DE PRIVILEGIOS:
        # El usuario solo puede asignar permisos que él mismo posee
        user_permissions = await get_user_permissions(user_id, db)
        requested_permissions = set(rol.permission)
        
        permisos_no_autorizados = requested_permissions - user_permissions
        
        if permisos_no_autorizados:
            # Obtener nombres de permisos no autorizados para mensaje claro
            stmt = select(Permiso.nombre).where(Permiso.id.in_(permisos_no_autorizados))
            result = await db.execute(stmt)
            nombres_permisos = result.scalars().all()
            
            raise HTTPException(
                status_code=403, 
                detail=f"No puede asignar permisos que no posee: {', '.join(nombres_permisos)}"
            )

        # Verificar si el rol ya existe
        stmr = select(Rol).where(Rol.nombre == rol.name)
        result = await db.execute(stmr)
        existing_rol = result.scalar_one_or_none()
        if existing_rol:
            raise HTTPException(status_code=400, detail="El rol ya existe")

        # Crear nuevo rol
        stmt = (
            insert(Rol)
            .values(nombre=rol.name)
            .returning(Rol.id)
        )

        result = await db.execute(stmt)
        new_rol_id = result.scalar()

        # Asignar permisos al nuevo rol
        for permiso_id in rol.permission:
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
            usuario_id=user_id,
            tabla_afectada="rol",
            tipo_operacion="INSERT",
            descripcion=f"Creacion de rol ID {new_rol_id} a nombre '{rol.name}'",
            id_registro=str(new_rol_id),
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

        return JSONResponse(content={"ok": True}, status_code=201)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update/{rol_id}")
async def actualizar_rol(
    request: Request,
    rol_id: int,
    data: RolCreate,
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
                Permiso.nombre == PERMISO_ROL
            )
            .limit(1)
        )

        tiene_permiso = await db.scalar(stmt)

        if not tiene_permiso:
            raise HTTPException(status_code=401, detail="No cuenta con permisos")

        # VALIDACIÓN DE ESCALADA DE PRIVILEGIOS:
        # El usuario solo puede asignar permisos que él mismo posee
        user_permissions = await get_user_permissions(user_id, db)
        requested_permissions = set(data.permission)
        
        permisos_no_autorizados = requested_permissions - user_permissions
        
        if permisos_no_autorizados:
            stmt = select(Permiso.nombre).where(Permiso.id.in_(permisos_no_autorizados))
            result = await db.execute(stmt)
            nombres_permisos = result.scalars().all()
            
            raise HTTPException(
                status_code=403, 
                detail=f"No puede asignar permisos que no posee: {', '.join(nombres_permisos)}"
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
            usuario_id=user_id,
            tabla_afectada="rol",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de rol ID {rol_id} a nombre '{data.name}'",
            id_registro=str(rol_id),
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
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete/{rol_id}")
async def borrar_rol(
    request: Request,
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
                Permiso.nombre == PERMISO_ROL
            )
            .limit(1)
        )

        tiene_permiso = await db.scalar(stmt)

        if not tiene_permiso:
            raise HTTPException(status_code=401, detail="No cuenta con permisos")

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

        # Eliminar permisos asociados al rol
        await db.execute(delete(RolPermiso).where(RolPermiso.rol_id == rol_id))

        # Eliminar el rol
        await db.execute(delete(Rol).where(Rol.id == rol_id))

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tabla_afectada="rol",
            tipo_operacion="DELETE",
            descripcion=f"Eliminación de rol ID {rol_id} con nombre '{existing_rol.nombre}'",
            id_registro=str(rol_id),
            datos_anteriores=datos_anteriores
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
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/permission/add")
async def agregar_permiso(
    request: Request,
    permission: PerCreate,
    db: AsyncSession = Depends(get_db)
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
                Permiso.nombre == PERMISO_ROL
            )
            .limit(1)
        )
        tiene_permiso = await db.scalar(stmt)

        if not tiene_permiso:
            raise HTTPException(status_code=401, detail="No cuenta con permisos")

        
        stmt = select(Permiso.id).where(Permiso.nombre == permission.name)
        permiso_id = await db.scalar(stmt)

        if permiso_id:
            raise HTTPException(status_code=400, detail="El nombre de permiso ya está en uso")

        stmt = select(Permiso.id).where(Permiso.menu_path == permission.menu_path)
        permiso_id = await db.scalar(stmt)

        if permiso_id:
            raise HTTPException(status_code=400, detail="El menu_path de permiso ya está en uso")

        stmt = (
            insert(Permiso)
            .values(nombre = permission.name, menu_path = permission.menu_path)
            .returning(Permiso.id)
        )
        permiso_id = await db.scalar(stmt)

        # Preparar datos para auditoría
        datos_nuevos = {
            "id": permiso_id,
            "nombre": permission.name,
            "menu_path": permission.menu_path,
        }

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tabla_afectada="permiso",
            tipo_operacion="INSERT",
            descripcion=f"Creacion de permioso ID {permiso_id} con nombre '{permission.name}'",
            id_registro=str(permiso_id),
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
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/permission/update/{permiso_id}")
async def actualizar_permiso(
    request: Request,
    permiso_id: int,
    permission: PerCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = verify_gateway_token(request)

        # Verificar permisos del usuario
        stmt = (
            select(1)
            .select_from(RolPermiso)
            .join(Permiso, Permiso.id == RolPermiso.permiso_id)
            .join(Usuario, Usuario.rol_id == RolPermiso.rol_id)
            .where(
                Usuario.numero_documento == user_id,
                Permiso.nombre == PERMISO_ROL
            )
            .limit(1)
        )
        tiene_permiso = await db.scalar(stmt)

        if not tiene_permiso:
            raise HTTPException(status_code=401, detail="No cuenta con permisos")

        # Verificar que el permiso existe
        stmt = select(Permiso).where(Permiso.id == permiso_id)
        permiso_existente = await db.scalar(stmt)

        if not permiso_existente:
            raise HTTPException(status_code=404, detail="Permiso no encontrado")

        # Guardar datos antiguos para auditoría
        datos_antiguos = {
            "id": permiso_existente.id,
            "nombre": permiso_existente.nombre,
            "menu_path": permiso_existente.menu_path,
        }

        # Verificar que el nuevo nombre no esté en uso (excepto por el mismo permiso)
        stmt = select(Permiso.id).where(
            Permiso.nombre == permission.name,
            Permiso.id != permiso_id
        )
        nombre_en_uso = await db.scalar(stmt)

        if nombre_en_uso:
            raise HTTPException(status_code=400, detail="El nombre de permiso ya está en uso")

        # Verificar que el nuevo menu_path no esté en uso (excepto por el mismo permiso)
        stmt = select(Permiso.id).where(
            Permiso.menu_path == permission.menu_path,
            Permiso.id != permiso_id
        )
        path_en_uso = await db.scalar(stmt)

        if path_en_uso:
            raise HTTPException(status_code=400, detail="El menu_path de permiso ya está en uso")

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

        # Preparar datos nuevos para auditoría
        datos_nuevos = {
            "id": permiso_id,
            "nombre": permission.name,
            "menu_path": permission.menu_path,
        }

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tabla_afectada="permiso",
            tipo_operacion="UPDATE",
            descripcion=f"Actualización de permiso ID {permiso_id} con nombre '{permission.name}'",
            id_registro=str(permiso_id),
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
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/permission/delete/{permiso_id}")
async def eliminar_permiso(
    request: Request,
    permiso_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        user_id = verify_gateway_token(request)

        # Verificar permisos del usuario
        stmt = (
            select(1)
            .select_from(RolPermiso)
            .join(Permiso, Permiso.id == RolPermiso.permiso_id)
            .join(Usuario, Usuario.rol_id == RolPermiso.rol_id)
            .where(
                Usuario.numero_documento == user_id,
                Permiso.nombre == PERMISO_ROL
            )
            .limit(1)
        )
        tiene_permiso = await db.scalar(stmt)

        if not tiene_permiso:
            raise HTTPException(status_code=401, detail="No cuenta con permisos")

        # Verificar que el permiso existe
        stmt = select(Permiso).where(Permiso.id == permiso_id)
        permiso_existente = await db.scalar(stmt)

        if not permiso_existente:
            raise HTTPException(status_code=404, detail="Permiso no encontrado")

        # Verificar si el permiso está siendo usado por algún rol
        stmt = select(RolPermiso.rol_id).where(RolPermiso.permiso_id == permiso_id).limit(1)
        permiso_en_uso = await db.scalar(stmt)

        if permiso_en_uso:
            raise HTTPException(
                status_code=400, 
                detail="No se puede eliminar el permiso porque está asignado a uno o más roles"
            )

        # Guardar datos antiguos para auditoría
        datos_antiguos = {
            "id": permiso_existente.id,
            "nombre": permiso_existente.nombre,
            "menu_path": permiso_existente.menu_path,
        }

        # Eliminar el permiso
        stmt = delete(Permiso).where(Permiso.id == permiso_id)
        await db.execute(stmt)

        # Guardar auditoría
        audit_result = await insert_auditoria(
            db=db,
            usuario_id=user_id,
            tabla_afectada="permiso",
            tipo_operacion="DELETE",
            descripcion=f"Eliminación de permiso ID {permiso_id} con nombre '{permiso_existente.nombre}'",
            id_registro=str(permiso_id),
            datos_antiguos=datos_antiguos
        )

        if not audit_result["ok"]:
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Error al guardar registro de auditoría"
            )

        # Commit de todo
        await db.commit()
        return JSONResponse(content={"ok": True, "message": "Permiso eliminado correctamente"}, status_code=200)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error en el servidor durante delete permission: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/permission/verify")
async def verificar_permiso(
    name: str,
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = (
            select(1)
            .select_from(RolPermiso)
            .join(Permiso, Permiso.id == RolPermiso.permiso_id)
            .join(Usuario, Usuario.rol_id == RolPermiso.rol_id)
            .where(
                Usuario.numero_documento == user_id,
                Permiso.nombre == name
            )
            .limit(1)
        )

        tiene_permiso = await db.scalar(stmt)

        if tiene_permiso is None:
            return JSONResponse(
                status_code=403,
                content={"ok": False, "message": "No cuenta con permisos"}
            )

        return JSONResponse(
            status_code=200,
            content={"ok": True, "message": "Permiso válido"}
        )

    except Exception as e:
        logger.error(f"Error en permission.verify: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

    