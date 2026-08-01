from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, insert
from pydantic import BaseModel, ConfigDict, Field
import logging
import os

#----- DB -----

from db.deps import get_db_managed
from db.models.rol import Rol
from db.models.permiso import Permiso
from db.models.rol_permiso import RolPermiso
from db.models.usuario import Usuario
from core.permissions import Permisos

router = APIRouter()
SECRET_KEY = os.getenv("SECRET_KEY")
PERMISO_ROL = Permisos.PERMISO_ROL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------- MODELOS ----------
class RolCreate(BaseModel):
    # El frontend envía {"nombre", "permisos"}; internamente el campo se llama
    # `permission`. populate_by_name permite aceptar tanto el alias como el
    # nombre del campo.
    model_config = ConfigDict(populate_by_name=True)

    nombre: str
    permission: list[int] = Field(..., alias="permisos")

class PerCreate(BaseModel):
    name:str
    menu_path: str

class Permission(BaseModel):
    permission_name: str
    user_id: int

from utils.insertLog import insert_auditoria
from utils.verify_token import verify_gateway_token, verify_service_token
from utils.permission_crud import (
    get_role_permissions,
    get_user_permission_names,
    get_user_permission_avaliable,
    get_user_rol_avaliable,
    get_permissions_by_rol_id,
)


async def _get_user_perm_names(rol_id: int, db: AsyncSession) -> set[str]:
    """Obtiene nombres de permisos del rol desde BD."""
    perms = await get_permissions_by_rol_id(rol_id, db)
    return {p["name"] for p in perms}


# ---------- ENDPOINTS ----------

@router.get("/all")
async def cargar_roles(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
    ):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if PERMISO_ROL not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para ver los roles"
        )

    data = await get_user_rol_avaliable(user_permission_names, db)

    return JSONResponse(content={"ok": True, "data": data}, status_code=200)

@router.get("/permissions")
async def cargar_permisos(
    request: Request,
    db: AsyncSession = Depends(get_db_managed),
    ):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if PERMISO_ROL not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para ver los permisos"
        )

    permission = await get_permissions_by_rol_id(token_data["rol_id"], db)

    return JSONResponse(content={"ok": True, "data": permission}, status_code=200)

@router.get("/role-permissions")
async def cargar_permiso_y_roles(
    request: Request,
    db: AsyncSession = Depends(get_db_managed)
    ):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if PERMISO_ROL not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para ver los roles y permisos"
        )

    data = await get_user_rol_avaliable(user_permission_names, db)
    logger.info(f"Permisos permitidos: {data}")

    return JSONResponse(content={"ok": True, "data": data}, status_code=200)

@router.post("/add")
async def agregar_rol(
    request: Request,
    rol: RolCreate,
    db: AsyncSession = Depends(get_db_managed),
    ):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if PERMISO_ROL not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para crear roles"
        )

    # Anti escalada: no se pueden otorgar a un rol permisos que el actor no tiene.
    requested_permission_names = await get_user_permission_names(rol.permission, db)
    if requested_permission_names - user_permission_names:
        raise HTTPException(
            status_code=403,
            detail=f"No puede asignar permisos que no posee."
        )

    stmr = select(Rol).where(Rol.nombre == rol.nombre)
    result = await db.execute(stmr)
    existing_rol = result.scalar_one_or_none()
    if existing_rol:
        logger.warning(f"[agregar_rol] El rol '{rol.nombre}' ya existe")
        raise HTTPException(status_code=400, detail="El rol ya existe")

    stmt = (
        insert(Rol)
        .values(nombre=rol.nombre)
        .returning(Rol.id)
    )

    result = await db.execute(stmt)
    new_rol_id = result.scalar()
    logger.info(f"[agregar_rol] Nuevo rol creado con ID: {new_rol_id}")

    for permiso_id in rol.permission:
        logger.info(f"[agregar_rol] Asignando permiso {permiso_id} al rol {new_rol_id}")
        rp = RolPermiso(rol_id=new_rol_id, permiso_id=permiso_id)
        db.add(rp)

    datos_nuevos = {
        "id": new_rol_id,
        "nombre": rol.nombre,
        "permisos": rol.permission
    }

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
        tipo_evento="CREACION_ROL",
        resultado="EXITOSO",
        detalle=f"Creacion de rol ID {new_rol_id} a nombre '{rol.nombre}'",
        datos_nuevos=datos_nuevos
    )

    if not audit_result["ok"]:
        logger.error(f"[agregar_rol] Error al guardar registro de auditoría: {audit_result}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error al guardar registro de auditoría"
        )

    await db.commit()
    logger.info(f"[agregar_rol] Rol creado exitosamente")
    return JSONResponse(content={"ok": True}, status_code=201)

@router.put("/update/{rol_id}")
async def actualizar_rol(
    request: Request,
    rol_id: int,
    data: RolCreate,
    db: AsyncSession = Depends(get_db_managed),
    ):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if PERMISO_ROL not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para actualizar roles"
        )

    # Anti escalada: no se pueden otorgar a un rol permisos que el actor no tiene.
    requested_permission_names = await get_user_permission_names(data.permission, db)
    if requested_permission_names - user_permission_names:
        raise HTTPException(
            status_code=403,
            detail=f"No puede asignar permisos que no posee."
        )

    stmr = select(Rol).where(Rol.id == rol_id)
    result = await db.execute(stmr)
    existing_rol = result.scalar_one_or_none()
    if not existing_rol:
        raise HTTPException(status_code=404, detail="El rol no existe")

    stmr_permisos = select(RolPermiso.permiso_id).where(RolPermiso.rol_id == rol_id)
    result_permisos = await db.execute(stmr_permisos)
    permisos_anteriores = [row[0] for row in result_permisos.fetchall()]

    datos_anteriores = {
        "id": existing_rol.id,
        "nombre": existing_rol.nombre,
        "permisos": permisos_anteriores
    }

    stmr = select(Rol).where(Rol.nombre == data.nombre, Rol.id != rol_id)
    result = await db.execute(stmr)
    duplicate_rol = result.scalar_one_or_none()
    if duplicate_rol:
        raise HTTPException(status_code=400, detail="El nombre de rol ya está en uso")

    stmr = update(Rol).where(Rol.id == rol_id).values(nombre=data.nombre)
    await db.execute(stmr)

    # Se reemplaza el set completo de permisos: borrar y volver a insertar.
    await db.execute(delete(RolPermiso).where(RolPermiso.rol_id == rol_id))
    for permiso_id in data.permission:
        rol_permiso = RolPermiso(rol_id=rol_id, permiso_id=permiso_id)
        db.add(rol_permiso)

    datos_nuevos = {
        "id": rol_id,
        "nombre": data.nombre,
        "permisos": data.permission
    }

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
        tipo_evento="ACTUALIZACION_ROL",
        resultado="EXITOSO",
        detalle=f"Actualización de rol ID {rol_id} a nombre '{data.nombre}'",
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

    return JSONResponse(content={"ok": True}, status_code=200)

@router.delete("/delete/{rol_id}")
async def eliminar_rol(
    request: Request,
    rol_id: int,
    db: AsyncSession = Depends(get_db_managed),
    ):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if PERMISO_ROL not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para eliminar roles"
        )

    stmr = select(Rol).where(Rol.id == rol_id)
    result = await db.execute(stmr)
    existing_rol = result.scalar_one_or_none()
    if not existing_rol:
        raise HTTPException(status_code=404, detail="El rol no existe")

    # Un rol en uso no se borra: dejaría usuarios sin rol (FK ON DELETE SET NULL).
    stmt_usuarios = select(Usuario.id).where(Usuario.rol_id == rol_id).limit(1)
    usuario_asignado = await db.scalar(stmt_usuarios)

    if usuario_asignado:
        raise HTTPException(
            status_code=400,
            detail="No se puede eliminar el rol porque está asignado a uno o más usuarios"
        )

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

    # Anti escalada: no se puede borrar un rol con permisos que el actor no tiene.
    permissions_name = {row.nombre for row in rows}
    if permissions_name - user_permission_names:
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

    await db.execute(delete(RolPermiso).where(RolPermiso.rol_id == rol_id))
    await db.execute(delete(Rol).where(Rol.id == rol_id))

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
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

    await db.commit()

    return JSONResponse(content={"ok": True}, status_code=200)

@router.post("/permission/add")
async def agregar_permiso(
    request: Request,
    permission: PerCreate,
    db: AsyncSession = Depends(get_db_managed)
    ):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if PERMISO_ROL not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para crear permisos"
        )

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
    # El creador se auto-asigna el permiso nuevo: si no, quedaría un permiso que
    # nadie puede administrar (las rutas exigen poseerlo para editarlo/borrarlo).
    rp = RolPermiso(rol_id=token_data["rol_id"], permiso_id=permiso_id)
    db.add(rp)

    datos_nuevos = {
        "id": permiso_id,
        "nombre": permission.name,
        "menu_path": permission.menu_path,
    }

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
        tipo_evento="CREACION_PERMISO",
        resultado="EXITOSO",
        detalle=f"Creacion de permiso ID {permiso_id} con nombre '{permission.name}'",
        datos_nuevos=datos_nuevos
    )

    if not audit_result["ok"]:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Error al guardar registro de auditoría"
        )

    await db.commit()
    return JSONResponse(content={"ok": True, "permiso_id": permiso_id}, status_code=201)

@router.put("/permission/update/{permiso_id}")
async def actualizar_permiso(
    request: Request,
    permiso_id: int,
    permission: PerCreate,
    db: AsyncSession = Depends(get_db_managed)
    ):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if PERMISO_ROL not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para actualizar permisos"
        )

    stmt = select(Permiso).where(Permiso.id == permiso_id)
    permiso_existente = await db.scalar(stmt)

    if not permiso_existente:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")

    if permiso_existente.nombre not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No puede actualizar un permiso que no posee"
        )

    stmt = select(Permiso.id).where(
        Permiso.nombre == permission.name,
        Permiso.id != permiso_id
    )
    nombre_en_uso = await db.scalar(stmt)

    if nombre_en_uso:
        raise HTTPException(status_code=400, detail="El nombre de permiso ya está en uso")

    stmt = (
        update(Permiso)
        .where(Permiso.id == permiso_id)
        .values(
            nombre=permission.name,
            menu_path=permission.menu_path
        )
    )
    await db.execute(stmt)

    datos_antiguos = {
        "id": permiso_existente.id,
        "nombre": permiso_existente.nombre,
        "menu_path": permiso_existente.menu_path,
    }

    datos_nuevos = {
        "id": permiso_id,
        "nombre": permission.name,
        "menu_path": permission.menu_path,
    }

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
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

    await db.commit()
    return JSONResponse(content={"ok": True, "message": "Permiso actualizado correctamente"}, status_code=200)

@router.delete("/permission/delete/{permiso_id}")
async def eliminar_permiso(
    request: Request,
    permiso_id: int,
    db: AsyncSession = Depends(get_db_managed)
    ):
    token_data = verify_gateway_token(request)
    user_permission_names = await _get_user_perm_names(token_data["rol_id"], db)

    if PERMISO_ROL not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No tiene permiso para eliminar permisos"
        )

    stmt = select(Permiso).where(Permiso.id == permiso_id)
    permiso_existente = await db.scalar(stmt)

    if not permiso_existente:
        raise HTTPException(status_code=404, detail="Permiso no encontrado")

    if permiso_existente.nombre not in user_permission_names:
        raise HTTPException(
            status_code=403,
            detail="No puede eliminar un permiso que no posee."
        )

    stmt_roles = select(RolPermiso.rol_id).where(RolPermiso.permiso_id == permiso_id)
    result_roles = await db.execute(stmt_roles)
    roles_afectados = result_roles.scalars().all()
    cantidad_roles = len(roles_afectados)

    await db.execute(delete(RolPermiso).where(RolPermiso.permiso_id == permiso_id))

    datos_antiguos = {
        "id": permiso_existente.id,
        "nombre": permiso_existente.nombre,
        "menu_path": permiso_existente.menu_path,
        "roles_afectados": cantidad_roles,
    }

    stmt = delete(Permiso).where(Permiso.id == permiso_id)
    await db.execute(stmt)

    audit_result = await insert_auditoria(
        db=db,
        usuario_id=token_data["user_id"],
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

    await db.commit()

    msg = f"Permiso eliminado correctamente"
    if cantidad_roles > 0:
        msg += f" (removido de {cantidad_roles} rol(es))"

    return JSONResponse(content={"ok": True, "message": msg}, status_code=200)

@router.post("/verify")
async def verificar_permiso(
    request: Request,
    permission: Permission,
    db: AsyncSession = Depends(get_db_managed)
    ):
    verify_service_token(request)

    stmt = (
        select(Permiso.nombre)
        .join(RolPermiso, RolPermiso.permiso_id == Permiso.id)
        .join(Rol, Rol.id == RolPermiso.rol_id)
        .join(Usuario, Usuario.rol_id == Rol.id)
        .where(Usuario.id == permission.user_id)
    )
    permissions_name = await db.scalars(stmt)
    permissions_name = permissions_name.all()

    tiene_permiso = permission.permission_name in permissions_name

    return JSONResponse(content={"ok": True, "tiene_permiso": tiene_permiso}, status_code=200)
