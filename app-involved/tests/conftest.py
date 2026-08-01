"""Fixtures compartidas para la suite de app-involved.

Usa una base Postgres dedicada (involved_test_db, mismo servidor que
involucrados_db) para no tocar datos reales. El aislamiento entre tests es por
TRUNCATE al terminar cada test, no por rollback: asyncpg no admite compartir la
conexión del fixture con las queries que dispara la app vía el cliente HTTP sin
choques de "otra operación en progreso".

verify_permission sale por HTTP hacia app-users, que no existe durante los
tests; se sustituye por un doble controlable en cada test (fixture `permisos`).
"""
import itertools
import os
from datetime import datetime, timedelta

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:Satc2026#Secure@postgres-involved:5432/involved_test_db",
)
# db/database.py crea el engine al importarse leyendo DATABASE_URL; get_db queda
# sobreescrito en los tests, pero el import no debe fallar.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.permission import Permisos
from db.deps import get_db
from db.models import Base
from db.models.involucrado import Involucrado
from db.models.auditoria import Auditoria
import main as main_module

engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

_doc_counter = itertools.count(1000000001)

# Los tokens de servicio se validan contra el secreto del caller esperado, no
# contra SERVICE_SECRET_KEY, así que hay que firmar con el secreto real.
TEST_CALLER_SERVICE = "sanctioning-service"
TEST_CALLER_SECRET = os.environ["SANCTIONING_SERVICE_SECRET"]
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

USER_ID = 42
ROL_ID = 1


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
            await conn.execute(text(
                f'TRUNCATE TABLE {", ".join(tablas)} RESTART IDENTITY CASCADE'
            ))


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
def permisos(monkeypatch):
    """Controla qué permisos "tiene" el usuario de prueba.

    Devuelve un set mutable: `permisos.add(...)` / `permisos.clear()` dentro del
    test cambia el resultado de verify_permission. Por defecto, sin permisos.
    """
    concedidos: set[str] = set()

    async def _fake_verify_permission(user_id: int, permission: str) -> bool:
        return permission in concedidos

    # Se parchea en routes.involved, donde el `from services.users import ...`
    # dejó ligado el nombre; parchear services.users no tendría efecto.
    import routes.involved as rutas
    monkeypatch.setattr(rutas, "verify_permission", _fake_verify_permission)
    return concedidos


@pytest.fixture
def con_gestion(permisos):
    permisos.add(Permisos.INVOLVED_MANAGE)
    return permisos


@pytest.fixture
def con_auditoria(permisos):
    permisos.add(Permisos.INVOLVED_LOG)
    return permisos


@pytest.fixture
def sin_usuarios(monkeypatch):
    """Neutraliza la llamada HTTP a app-users que enriquece el log."""
    async def _fake_get_user_info(user_ids):
        return {}

    import routes.involved as rutas
    monkeypatch.setattr(rutas, "get_user_info", _fake_get_user_info)


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    main_module.app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    main_module.app.dependency_overrides.clear()


def gateway_headers(user_id: int = USER_ID, rol_id: int = ROL_ID) -> dict:
    return {
        "x-gateway-token": os.environ["SECRET_GATEWAY"],
        "X-Gateway-User-Id": str(user_id),
        "X-Gateway-Role-Id": str(rol_id),
    }


def service_headers() -> dict:
    token = jwt.encode(
        {
            "service": TEST_CALLER_SERVICE,
            "exp": datetime.utcnow() + timedelta(minutes=5),
            "iat": datetime.utcnow(),
        },
        TEST_CALLER_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    return {"x-service-token": token}


@pytest_asyncio.fixture
async def make_involucrado(db_session):
    async def _make(**overrides) -> Involucrado:
        defaults = dict(
            numero_documento=next(_doc_counter),
            digito_verificacion=None,
            tipo_documento="CC",
            nombre="Persona Prueba",
            celular=3001234567,
            correo="persona@test.com",
            direccion="Calle 1 # 2-3",
        )
        defaults.update(overrides)
        inv = Involucrado(**defaults)
        db_session.add(inv)
        await db_session.flush()
        return inv
    return _make


@pytest_asyncio.fixture
async def make_auditoria(db_session):
    async def _make(**overrides) -> Auditoria:
        defaults = dict(
            usuario_id=USER_ID,
            tipo_evento="CREAR_INVOLUCRADO",
            resultado="EXITOSO",
            fecha=datetime.now(),
            detalle="Detalle de prueba",
        )
        defaults.update(overrides)
        aud = Auditoria(**defaults)
        db_session.add(aud)
        await db_session.flush()
        return aud
    return _make
