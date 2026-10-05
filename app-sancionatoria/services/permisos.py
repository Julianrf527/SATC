"""Autorización por permiso de los endpoints de app-sancionatoria.

El gateway solo autentica (sesión): no controla permisos por ruta. Cada
endpoint exige aquí el mismo permiso que la pantalla del frontend que lo
consume (frontend/src/app/App.tsx):

  /file/manage        -> sancionatorio_gestionar (solo los expedientes a cargo)
  /file/consult       -> sancionatorio_consultar (todos, solo lectura)
  /file/assign_manage -> sancionatorio_asignar
  /file/alerts        -> sancionatorio_alertas

Regla de lectura de un expediente (la misma de /infraction/expedientes/completo):
**consultar ve todo; gestionar ve solo lo suyo.** Si el expediente es ajeno o no
existe se responde 403 (no 404) para no revelar qué ids existen.

Los endpoints cerrados en la auditoría de permisos (2026-10) llaman a estas
funciones y no a ``verify_permission`` directamente: así los tests sustituyen
``services.permisos.verify_permission`` en un solo sitio.
"""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.permission import Permission
from db.models.expediente import Expediente
from services.users import verify_permission

SIN_PERMISOS_EXPEDIENTE = "Sin permisos sobre este expediente"


async def tiene_alguno(user_id: int, *permisos: str) -> bool:
    for permiso in permisos:
        if await verify_permission(user_id, permiso):
            return True
    return False


async def exigir_alguno(user_id: int, *permisos: str) -> None:
    if not await tiene_alguno(user_id, *permisos):
        raise HTTPException(status_code=403, detail="Sin permisos")


async def _fila_expediente(db: AsyncSession, expediente_id: int):
    return (await db.execute(
        select(Expediente.id, Expediente.radicado, Expediente.encargado_id)
        .where(Expediente.id == expediente_id)
    )).fetchone()


async def exigir_lectura_expediente(db: AsyncSession, expediente_id: int, user_id: int):
    """Lectura de un expediente: ``sancionatorio_consultar`` (cualquiera), o
    ``sancionatorio_gestionar`` y ser el encargado. Devuelve (id, radicado,
    encargado_id); 403 si no hay permiso, si es ajeno o si no existe."""
    if await verify_permission(user_id, Permission.FILE_CONSULT):
        row = await _fila_expediente(db, expediente_id)
    else:
        await exigir_alguno(user_id, Permission.FILE_MANAGE)
        row = await _fila_expediente(db, expediente_id)
        if row is not None and row.encargado_id != user_id:
            row = None
    if row is None:
        raise HTTPException(status_code=403, detail=SIN_PERMISOS_EXPEDIENTE)
    return row


async def exigir_escritura_expediente(db: AsyncSession, expediente_id: int, user_id: int):
    """Escritura sobre un expediente: ``sancionatorio_gestionar`` y ser el
    encargado. Devuelve (id, radicado, encargado_id); 403 en otro caso."""
    await exigir_alguno(user_id, Permission.FILE_MANAGE)
    row = await _fila_expediente(db, expediente_id)
    if row is None or row.encargado_id != user_id:
        raise HTTPException(status_code=403, detail=SIN_PERMISOS_EXPEDIENTE)
    return row
