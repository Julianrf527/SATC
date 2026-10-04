"""
Fixtures compartidas para la suite de app-docs.

Usa una base Postgres dedicada (docs_test_db, mismo servidor que documentos_db)
para no tocar datos reales. Cada test corre con una sesión normal contra esa
base; el aislamiento se logra con TRUNCATE al terminar cada test (no por rollback:
asyncpg no admite compartir la conexión del fixture con las queries que dispara
la app vía el cliente HTTP sin choques de "otra operación en progreso").

Los servicios externos (users, notifications, MinIO, ClamAV) se monkeypatchean:
no hay red hacia otros contenedores dentro del test.
"""
import os

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:Satc2026#Secure@postgres-docs:5432/docs_test_db",
)
# db/database.py crea un engine a nivel de módulo al importarse. No se usa en los
# tests (get_db queda sobreescrito), pero DATABASE_URL debe apuntar a algo válido.
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)

import itertools
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.deps import get_db
from db.models import Base
from db.models.documentos import Documento
from db.models.versiones_documento import VersionDocumento
from db.models.asignaciones_revisores import AsignacionRevisor
from db.models.file_hash import FileHash
from utils.generate_service_jwt import generate_service_jwt
import main as main_module

_VIEW_SQL = """
CREATE OR REPLACE VIEW vista_documentos_detalle AS
SELECT d.id, d.id AS documento_id, d.nombre, d.descripcion, d.tipo_archivo,
       d.estado, d.origen, d.version_actual, d.numero_devoluciones, d.usuario_creador_id,
       d.fecha_creacion, d.fecha_ultima_actualizacion,
       COALESCE(rev_count.total_revisiones, 0) AS total_revisiones,
       COALESCE(asig_count.total_revisores, 0) AS total_revisores
FROM documentos d
LEFT JOIN (SELECT documento_id, COUNT(*) AS total_revisiones FROM revisiones GROUP BY documento_id) rev_count ON rev_count.documento_id = d.id
LEFT JOIN (SELECT documento_id, COUNT(*) AS total_revisores FROM asignaciones_revisores GROUP BY documento_id) asig_count ON asig_count.documento_id = d.id
"""

engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
_id_counter = itertools.count(1)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _crear_esquema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(_VIEW_SQL))
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _limpiar_tablas():
    yield
    async with engine.begin() as conn:
        tablas = (await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ))).scalars().all()
        if tablas:
            await conn.execute(text(f'TRUNCATE TABLE {", ".join(tablas)} RESTART IDENTITY CASCADE'))


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    main_module.app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    main_module.app.dependency_overrides.clear()


def gateway_headers(user_id: int, rol_id: int = 1) -> dict:
    return {
        "x-gateway-token": os.environ["SECRET_GATEWAY"],
        "X-Gateway-User-Id": str(user_id),
        "X-Gateway-Role-Id": str(rol_id),
    }


def service_headers() -> dict:
    # app-docs valida contra el secreto de cada caller esperado, no el propio
    # SERVICE_SECRET_KEY. Simulamos un caller real con su secreto real.
    return {"x-service-token": generate_service_jwt("sanctioning-service", os.environ["SANCTIONING_SERVICE_SECRET"])}


@pytest_asyncio.fixture
async def make_documento(db_session):
    async def _make(creador_id: int = 1, estado: str = "en_revision", **overrides) -> Documento:
        n = next(_id_counter)
        defaults = dict(
            nombre=f"Documento {n}",
            descripcion="Desc de prueba",
            tipo_archivo="pdf",
            usuario_creador_id=creador_id,
            estado=estado,
            version_actual=1,
            numero_devoluciones=0,
        )
        defaults.update(overrides)
        doc = Documento(**defaults)
        db_session.add(doc)
        await db_session.flush()
        return doc

    return _make


@pytest_asyncio.fixture
async def make_version(db_session):
    async def _make(documento_id: int, numero_version: int = 1, **overrides) -> VersionDocumento:
        n = next(_id_counter)
        defaults = dict(
            documento_id=documento_id,
            numero_version=numero_version,
            archivo_url=f"satc-documentos/hash{n}/archivo.pdf",
            archivo_nombre_original="archivo.pdf",
            archivo_size=1234,
            usuario_subida_id=1,
            comentario="v",
        )
        defaults.update(overrides)
        ver = VersionDocumento(**defaults)
        db_session.add(ver)
        await db_session.flush()
        return ver

    return _make


@pytest_asyncio.fixture
async def make_asignacion(db_session):
    async def _make(documento_id: int, revisor_id: int) -> AsignacionRevisor:
        asig = AsignacionRevisor(documento_id=documento_id, revisor_id=revisor_id, notificado=True)
        db_session.add(asig)
        await db_session.flush()
        return asig

    return _make


@pytest_asyncio.fixture
async def make_file_hash(db_session):
    async def _make(**overrides) -> FileHash:
        n = next(_id_counter)
        defaults = dict(
            file_hash=f"hash{n:064d}"[:64],
            file_url=f"satc-documentos/hash{n}/archivo.pdf",
            content_type="application/pdf",
            file_size=1234,
            numero_usos=0,
        )
        defaults.update(overrides)
        fh = FileHash(**defaults)
        db_session.add(fh)
        await db_session.flush()
        return fh

    return _make
