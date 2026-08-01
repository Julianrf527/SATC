"""
Seedeo de datos iniciales para expedientes_db
"""
from sqlalchemy import select
from db.database import SessionLocal
from db.models.municipio import Municipio
from db.models.vereda import Vereda
from db.models.recurso_afectado import RecursoAfectado
from db.models.tipo_cesacion import TipoCesacion
from db.models.tipo_medida import TipoMedida
from db.models.tipo_notificacion import TipoNotificacion
from db.models.tipo_sancion import TipoSancion

from .seed_data import MUNICIPIOS, VEREDAS, RECURSOS, TIPO_CESACION, TIPO_MEDIDA, TIPO_NOTIFICACION, TIPO_SANCION


async def seed_initial_data():
    async with SessionLocal() as session:
        print("Iniciando seedeo de expedientes_db...")
        try:
            ins = {k: 0 for k in ["municipios", "veredas", "recursos", "cesaciones", "medidas", "notificaciones", "sanciones"]}

            existing_municipios = set((await session.execute(select(Municipio.id))).scalars().all())
            for id_mun, nombre in MUNICIPIOS:
                if id_mun not in existing_municipios:
                    session.add(Municipio(id=id_mun, nombre=nombre)); ins["municipios"] += 1

            existing_veredas = set((await session.execute(select(Vereda.id))).scalars().all())
            for id_ver, nombre, municipio_id in VEREDAS:
                if id_ver not in existing_veredas:
                    session.add(Vereda(id=id_ver, nombre=nombre, municipio_id=municipio_id)); ins["veredas"] += 1

            existing_recursos = set((await session.execute(select(RecursoAfectado.id))).scalars().all())
            for id_rec, nombre in RECURSOS:
                if id_rec not in existing_recursos:
                    session.add(RecursoAfectado(id=id_rec, nombre=nombre)); ins["recursos"] += 1

            existing_tc = set((await session.execute(select(TipoCesacion.id))).scalars().all())
            for id_tc, nombre in TIPO_CESACION:
                if id_tc not in existing_tc:
                    session.add(TipoCesacion(id=id_tc, nombre=nombre)); ins["cesaciones"] += 1

            existing_tm = set((await session.execute(select(TipoMedida.id))).scalars().all())
            for id_tm, nombre in TIPO_MEDIDA:
                if id_tm not in existing_tm:
                    session.add(TipoMedida(id=id_tm, nombre=nombre)); ins["medidas"] += 1

            existing_tn = set((await session.execute(select(TipoNotificacion.id))).scalars().all())
            for id_tn, nombre in TIPO_NOTIFICACION:
                if id_tn not in existing_tn:
                    session.add(TipoNotificacion(id=id_tn, nombre=nombre)); ins["notificaciones"] += 1

            existing_ts = set((await session.execute(select(TipoSancion.id))).scalars().all())
            for id_ts, nombre in TIPO_SANCION:
                if id_ts not in existing_ts:
                    session.add(TipoSancion(id=id_ts, nombre=nombre)); ins["sanciones"] += 1

            await session.flush()
            await session.commit()
            print(f"✓ Seedeo completado exitosamente {ins}\n")

        except Exception as e:
            await session.rollback()
            print(f"✗ Error durante seedeo: {e}\n")
            raise
