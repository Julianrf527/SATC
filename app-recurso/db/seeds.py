"""Seed idempotente de recurso_db: municipios, veredas, tipo_fuente, fuente y
tipo_notificacion. Solo inserta lo que falta (por id en municipio/vereda, por
nombre en los catálogos)."""
from sqlalchemy import select, text

from db.database import SessionLocal
from db.models import Fuente, Municipio, TipoFuente, TipoNotificacion, Vereda
from .seed_data import FUENTES, MUNICIPIOS, TIPOS_FUENTE, TIPOS_NOTIFICACION, VEREDAS


async def _insertar_por_nombre(session, modelo, nombres: list[str]) -> int:
    existentes = set((await session.execute(select(modelo.nombre))).scalars().all())
    nuevos = [modelo(nombre=n) for n in nombres if n not in existentes]
    session.add_all(nuevos)
    return len(nuevos)


async def seed_initial_data():
    async with SessionLocal() as session:
        try:
            existentes = set((await session.execute(select(Municipio.id))).scalars().all())
            municipios = [Municipio(id=i, nombre=n) for i, n in MUNICIPIOS if i not in existentes]
            session.add_all(municipios)
            await session.flush()

            existentes = set((await session.execute(select(Vereda.id))).scalars().all())
            veredas = [Vereda(id=i, nombre=n, municipio_id=m) for i, n, m in VEREDAS if i not in existentes]
            session.add_all(veredas)

            tipos_fuente = await _insertar_por_nombre(session, TipoFuente, TIPOS_FUENTE)
            fuentes = await _insertar_por_nombre(session, Fuente, FUENTES)
            tipos_notif = await _insertar_por_nombre(session, TipoNotificacion, TIPOS_NOTIFICACION)
            await session.flush()

            # Los ids de municipio/vereda se insertan explícitos: la secuencia
            # queda atrás y el próximo INSERT sin id chocaría.
            for tabla in ("municipio", "vereda"):
                await session.execute(
                    text(
                        f"SELECT setval(pg_get_serial_sequence('{tabla}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {tabla}), 1))"
                    )
                )
            await session.commit()
            print(
                f"Seed recurso_db: {len(municipios)} municipios, {len(veredas)} veredas, "
                f"{tipos_fuente} tipos de fuente, {fuentes} fuentes, {tipos_notif} tipos de notificación"
            )
        except Exception as e:
            await session.rollback()
            print(f"Error en seed de recurso_db: {e}")
            raise
