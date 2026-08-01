"""
Fixtures compartidas. Usa una base de datos Postgres separada
(expedientes_test_db, mismo servidor que expedientes_db) para no tocar datos
reales.

Cada test usa una sesión normal (igual que get_db() en producción) contra esa
base — el código bajo prueba hace sus propios commit()s de verdad. El
aislamiento entre tests no es por rollback de transacción (asyncpg no admite
compartir una misma conexión entre el setup del fixture y las queries que
dispara la app vía el cliente HTTP sin choques de "otra operación en
progreso"); en vez de eso, se limpian las tablas con TRUNCATE al terminar
cada test.
"""
import os

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:Satc2026#Secure@postgres-sanctioning:5432/expedientes_test_db",
)
# db/database.py lee DATABASE_URL al importarse (crea un engine a nivel de
# módulo). No se usa para los tests (get_db queda sobreescrito), pero debe
# apuntar a algo válido para que el import no falle si faltara.
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)

import itertools
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.deps import get_db
from db.models import Base
from db.models.expediente import Expediente
from db.models.tipo_medida import TipoMedida
from db.models.tipo_cesacion import TipoCesacion
from db.models.tipo_sancion import TipoSancion
from db.models.acto_administrativo import ActoAdministrativo
from db.models.notificacion import Notificacion
import main as main_module

engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
_radicado_counter = itertools.count(1)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _crear_esquema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
    # base_url incluye el prefijo "/stage" con el que main.py monta el router
    # (app.include_router(stage.router, prefix="/stage")), así los tests
    # llaman con las mismas rutas relativas que expone el router.
    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test/stage") as ac:
        yield ac
    main_module.app.dependency_overrides.clear()


def gateway_headers(user_id: int, rol_id: int = 1) -> dict:
    return {
        "x-gateway-token": os.environ["SECRET_GATEWAY"],
        "X-Gateway-User-Id": str(user_id),
        "X-Gateway-Role-Id": str(rol_id),
    }


@pytest_asyncio.fixture
async def make_expediente(db_session):
    async def _make(encargado_id: int = 1, **overrides) -> Expediente:
        n = next(_radicado_counter)
        defaults = dict(
            radicado=f"TEST-{n:06d}",
            expediente=f"E{n}",
            motivo_afectacion="Motivo de prueba",
            encargado_id=encargado_id,
            direccion="Vereda de prueba",
        )
        defaults.update(overrides)
        exp = Expediente(**defaults)
        db_session.add(exp)
        await db_session.flush()
        return exp

    return _make


@pytest_asyncio.fixture
async def tipo_medida(db_session) -> TipoMedida:
    tipo = TipoMedida(nombre="Decomiso")
    db_session.add(tipo)
    await db_session.flush()
    return tipo


@pytest_asyncio.fixture
async def tipo_cesacion(db_session) -> TipoCesacion:
    tipo = TipoCesacion(nombre="Cumplimiento")
    db_session.add(tipo)
    await db_session.flush()
    return tipo


@pytest_asyncio.fixture
async def tipo_sancion(db_session) -> TipoSancion:
    tipo = TipoSancion(nombre="Multa")
    db_session.add(tipo)
    await db_session.flush()
    return tipo


@pytest_asyncio.fixture
async def make_acto_administrativo(db_session):
    async def _make(**overrides) -> ActoAdministrativo:
        defaults = dict(tipo_acto="comunicacion", numerado=1)
        defaults.update(overrides)
        acto = ActoAdministrativo(**defaults)
        db_session.add(acto)
        await db_session.flush()
        return acto

    return _make


@pytest_asyncio.fixture
async def make_notificacion(db_session):
    async def _make(acto_administrativo_id: int, notificacion_exitosa: bool = True, **overrides) -> Notificacion:
        defaults = dict(acto_administrativo_id=acto_administrativo_id, notificacion_exitosa=notificacion_exitosa)
        defaults.update(overrides)
        notif = Notificacion(**defaults)
        db_session.add(notif)
        await db_session.flush()
        return notif

    return _make
