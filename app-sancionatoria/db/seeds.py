"""
Seedeo de datos iniciales para expedientes_db
Municipios y Veredas
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.database import SessionLocal
from db.models.municipio import Municipio
from db.models.vereda import Vereda
from .seed_data import MUNICIPIOS, VEREDAS


async def seed_initial_data():
    """
    Ejecuta el seedeo de municipios y veredas.
    Solo inserta si no existen ya en la BD.
    """
    async with SessionLocal() as session:
        # Verificar si ya existen municipios
        result = await session.execute(select(Municipio).limit(1))
        if result.scalars().first():
            print("Datos iniciales ya existen en expedientes_db, skipping seedeo")
            return

        print("Iniciando seedeo de expedientes_db...")

        try:
            # 1. Insertar municipios
            for id_mun, nombre in MUNICIPIOS:
                municipio = Municipio(id=id_mun, nombre=nombre)
                session.add(municipio)
            await session.flush()
            print(f"✓ Insertados {len(MUNICIPIOS)} municipios")

            # 2. Insertar veredas
            for id_ver, nombre, municipio_id in VEREDAS:
                vereda = Vereda(id=id_ver, nombre=nombre, municipio_id=municipio_id)
                session.add(vereda)
            await session.flush()
            print(f"✓ Insertadas {len(VEREDAS)} veredas")

            # Commit
            await session.commit()
            print("✓ Seedeo completado exitosamente\n")

        except Exception as e:
            await session.rollback()
            print(f"✗ Error durante seedeo: {e}\n")
            raise
