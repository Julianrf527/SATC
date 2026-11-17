"""Catálogos de la información base (plan §3.1). Solo lectura (``requiere_lectura``).

Prefijo en main.py: ``/catalogos``.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.acceso import requiere_lectura
from db.deps import get_db_managed
from db.models import Fuente, Municipio, TipoFuente, TipoNotificacion, UsoAgua, Vereda

router = APIRouter()


async def _municipios(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(
        select(
            Municipio.id.label("m_id"),
            Municipio.nombre.label("m_nombre"),
            Vereda.id.label("v_id"),
            Vereda.nombre.label("v_nombre"),
        )
        .join(Vereda, Vereda.municipio_id == Municipio.id, isouter=True)
        .order_by(Municipio.nombre, Vereda.nombre)
    )).mappings().all()
    municipios: dict[int, dict] = {}
    for r in rows:
        m = municipios.setdefault(r["m_id"], {"id": r["m_id"], "nombre": r["m_nombre"], "veredas": []})
        if r["v_id"] is not None:
            m["veredas"].append({"id": r["v_id"], "nombre": r["v_nombre"]})
    return list(municipios.values())


async def _por_nombre(db: AsyncSession, modelo) -> list[dict]:
    filas = (await db.execute(select(modelo).order_by(modelo.nombre))).scalars().all()
    return [{"id": f.id, "nombre": f.nombre} for f in filas]


def _usos() -> list[str]:
    return [u.value for u in UsoAgua]


@router.get("")
async def todos_los_catalogos(request: Request, db: AsyncSession = Depends(get_db_managed)):
    """Todos los catálogos en una sola respuesta (formulario de información base)."""
    await requiere_lectura(request)
    return {
        "ok": True,
        "data": {
            "municipios": await _municipios(db),
            "tipos_fuente": await _por_nombre(db, TipoFuente),
            "fuentes": await _por_nombre(db, Fuente),
            "usos": _usos(),
            "tipos_notificacion": await _por_nombre(db, TipoNotificacion),
        },
    }


@router.get("/municipios")
async def municipios_con_veredas(request: Request, db: AsyncSession = Depends(get_db_managed)):
    await requiere_lectura(request)
    return {"ok": True, "data": await _municipios(db)}


@router.get("/tipos-fuente")
async def tipos_fuente(request: Request, db: AsyncSession = Depends(get_db_managed)):
    await requiere_lectura(request)
    return {"ok": True, "data": await _por_nombre(db, TipoFuente)}


@router.get("/fuentes")
async def fuentes(request: Request, db: AsyncSession = Depends(get_db_managed)):
    await requiere_lectura(request)
    return {"ok": True, "data": await _por_nombre(db, Fuente)}


@router.get("/usos")
async def usos(request: Request):
    await requiere_lectura(request)
    return {"ok": True, "data": _usos()}


@router.get("/tipos-notificacion")
async def tipos_notificacion(request: Request, db: AsyncSession = Depends(get_db_managed)):
    await requiere_lectura(request)
    return {"ok": True, "data": await _por_nombre(db, TipoNotificacion)}
