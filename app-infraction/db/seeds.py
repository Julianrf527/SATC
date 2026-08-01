"""
Seedeo de datos iniciales para expedientes_db
Municipios, Veredas, Recursos Afectados y Tipos de Afectacion
"""
from sqlalchemy import select
from db.database import SessionLocal
from db.models.municipio import Municipio
from db.models.vereda import Vereda
from db.models.recurso_afectado import RecursoAfectado
from db.models.tipo_afectacion import TipoAfectacion
from db.models.tipo_medida import TipoMedida
from db.models.tipo_notificacion import TipoNotificacion
from .seed_data import MUNICIPIOS, RECUROS, TIPOS_AFECTACION, VEREDAS, TIPO_MEDIDA, TIPO_NOTIFICACION


async def seed_initial_data():
    """
    Ejecuta el seedeo de municipios, veredas, recursos afectados y tipos de afectacion.
    Solo inserta los registros que faltan para que el proceso sea idempotente.
    """
    async with SessionLocal() as session:
        print("Iniciando seedeo de expedientes_db...")

        try:
            inserted_municipios = 0
            inserted_veredas = 0
            inserted_recursos = 0
            inserted_tipos = 0
            inserted_tipo_medida = 0

            existing_municipios = set(
                (await session.execute(select(Municipio.id))).scalars().all()
            )
            for id_mun, nombre in MUNICIPIOS:
                if id_mun in existing_municipios:
                    continue
                session.add(Municipio(id=id_mun, nombre=nombre))
                inserted_municipios += 1

            existing_veredas = set(
                (await session.execute(select(Vereda.id))).scalars().all()
            )
            for id_ver, nombre, municipio_id in VEREDAS:
                if id_ver in existing_veredas:
                    continue
                session.add(Vereda(id=id_ver, nombre=nombre, municipio_id=municipio_id))
                inserted_veredas += 1

            existing_recursos = set(
                (await session.execute(select(RecursoAfectado.id))).scalars().all()
            )
            for id_rec, nombre in RECUROS:
                if id_rec in existing_recursos:
                    continue
                session.add(RecursoAfectado(id=id_rec, nombre=nombre))
                inserted_recursos += 1

            await session.flush()

            existing_tipos = set(
                (await session.execute(select(TipoAfectacion.id))).scalars().all()
            )
            for id_tipo, nombre, recurso_id in TIPOS_AFECTACION:
                if id_tipo in existing_tipos:
                    continue
                session.add(TipoAfectacion(id=id_tipo, nombre=nombre, recurso_id=recurso_id))
                inserted_tipos += 1

            existing_tipo_medida = set(
                (await session.execute(select(TipoMedida.id))).scalars().all()
            )
            for id_tm, nombre in TIPO_MEDIDA:
                if id_tm in existing_tipo_medida:
                    continue
                session.add(TipoMedida(id=id_tm, nombre=nombre))
                inserted_tipo_medida += 1

            inserted_tipo_notificacion = 0
            existing_tipo_notificacion = set(
                (await session.execute(select(TipoNotificacion.id))).scalars().all()
            )
            for id_tn, nombre in TIPO_NOTIFICACION:
                if id_tn in existing_tipo_notificacion:
                    continue
                session.add(TipoNotificacion(id=id_tn, nombre=nombre))
                inserted_tipo_notificacion += 1

            await session.flush()
            await session.commit()
            print(
                "✓ Seedeo completado exitosamente "
                f"(municipios={inserted_municipios}, veredas={inserted_veredas}, "
                f"recursos={inserted_recursos}, tipos_afectacion={inserted_tipos}, "
                f"tipos_medida={inserted_tipo_medida}, tipos_notificacion={inserted_tipo_notificacion})\n"
            )

        except Exception as e:
            await session.rollback()
            print(f"✗ Error durante seedeo: {e}\n")
            raise
