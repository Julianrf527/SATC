"""
Fixtures compartidas para la suite de app-users.

Usa una base de datos Postgres dedicada (users_test_db, mismo servidor que
user_db) para no tocar datos reales. Igual que en app-sancionatoria, el
aislamiento entre tests es por TRUNCATE al terminar cada test (no por rollback:
asyncpg no admite compartir la conexión del fixture con las queries que dispara
la app vía el cliente HTTP sin choques de "otra operación en progreso").

Cada endpoint valida permisos consultando la BD en tiempo real, así que los
tests siembran roles/permisos/usuarios reales según lo que necesiten.
"""
import os
from datetime import datetime, timedelta

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:Satc2026#Secure@postgres-users:5432/users_test_db",
)
# db/database.py crea un engine a nivel de módulo leyendo DATABASE_URL al
# importarse. get_db queda sobreescrito en los tests, pero el import no debe
# fallar, así que lo apuntamos a la misma base de test.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import itertools

import pytest
import pytest_asyncio
from jose import jwt
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.deps import get_db
from db.models import Base
from db.models.usuario import Usuario
from db.models.rol import Rol
from db.models.permiso import Permiso
from db.models.rol_permiso import RolPermiso
from db.models.notificacion import Notificacion
from utils.passwords import hash_password
import main as main_module

engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

_doc_counter = itertools.count(100001)
_perm_counter = itertools.count(1)

# Los tokens de servicio se validan contra el secreto de cada caller esperado,
# no contra SERVICE_SECRET_KEY (ese solo firma lo que app-users emite), así que
# hay que firmar con el secreto real del caller simulado.
TEST_CALLER_SERVICE = "sanctioning-service"
TEST_CALLER_SECRET = os.environ["SANCTIONING_SERVICE_SECRET"]
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
TEST_PASSWORD = "Segura123!"
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


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


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    main_module.app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=main_module.app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    main_module.app.dependency_overrides.clear()


def gateway_headers(user_id: int, rol_id: int) -> dict:
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


class FakeRedis:
    """Redis async mínimo en memoria para no tocar el satc-redis compartido."""

    def __init__(self):
        self.store = {}

    async def set(self, key, value, ex=None):
        self.store[key] = str(value)

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, *keys):
        for k in keys:
            self.store.pop(k, None)


@pytest.fixture(autouse=True)
def fake_redis():
    """Instala un Redis falso como cliente global de sesiones durante cada test.

    ASGITransport no dispara el evento startup, así que init_redis() nunca corre
    y get_redis_client() devolvería None (login daría 503). Además evita escribir
    claves session:user:* en el Redis real compartido con el sistema en vivo.
    """
    import utils.redis_session as rs
    original = rs.redis_client
    rs.redis_client = FakeRedis()
    yield rs.redis_client
    rs.redis_client = original


@pytest_asyncio.fixture
async def make_permiso(db_session):
    async def _make(nombre: str = None, menu_path: str = "") -> Permiso:
        if nombre is None:
            nombre = f"perm_{next(_perm_counter)}"
        p = Permiso(nombre=nombre, menu_path=menu_path)
        db_session.add(p)
        await db_session.flush()
        return p
    return _make


@pytest_asyncio.fixture
async def make_rol(db_session):
    async def _make(nombre: str, permisos: list[Permiso] = None) -> Rol:
        rol = Rol(nombre=nombre)
        db_session.add(rol)
        await db_session.flush()
        for p in (permisos or []):
            db_session.add(RolPermiso(rol_id=rol.id, permiso_id=p.id))
        await db_session.flush()
        return rol
    return _make


@pytest_asyncio.fixture
async def make_usuario(db_session):
    async def _make(rol_id: int, activo: bool = True, correo: str = None, **overrides) -> Usuario:
        doc = overrides.pop("numero_documento", next(_doc_counter))
        if correo is None:
            correo = f"user{doc}@test.com"
        defaults = dict(
            numero_documento=doc,
            primer_nombre="Test",
            primer_apellido="User",
            correo=correo,
            hash_contrasena=TEST_PASSWORD_HASH,
            activo=activo,
            rol_id=rol_id,
        )
        defaults.update(overrides)
        u = Usuario(**defaults)
        db_session.add(u)
        await db_session.flush()
        return u
    return _make


@pytest_asyncio.fixture
async def make_notificacion(db_session):
    async def _make(usuario_id: int, **overrides) -> Notificacion:
        defaults = dict(
            usuario_id=usuario_id,
            mensaje="Mensaje de prueba",
            id_vinculada="EXP-1",
            tipo="alerta",
            fecha_creacion=datetime.utcnow(),
        )
        defaults.update(overrides)
        n = Notificacion(**defaults)
        db_session.add(n)
        await db_session.flush()
        return n
    return _make
