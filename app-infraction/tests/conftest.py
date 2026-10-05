"""
Fixtures compartidas. Usa una base de datos Postgres separada
(infraction_test_db, mismo servidor que infracciones_db) para no tocar datos
reales.

Cada test usa una sesión normal (igual que get_db() en producción) contra esa
base — el código bajo prueba hace sus propios commit()s de verdad. El
aislamiento entre tests se hace con TRUNCATE de todas las tablas al terminar
cada test (no por rollback: asyncpg no admite compartir una misma conexión
entre el setup del fixture y las queries que dispara la app vía el cliente
HTTP sin choques de "otra operación en progreso").
"""
import os

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:Satc2026#Secure@postgres-infraction:5432/infraction_test_db",
)
# db/database.py lee DATABASE_URL al importarse (crea un engine a nivel de
# módulo). No se usa en los tests (get_db queda sobreescrito), pero debe
# apuntar a algo válido para que el import no falle.
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("SECRET_GATEWAY", "test-gateway-secret")
os.environ.setdefault("SERVICE_SECRET_KEY", "test-service-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

import itertools
from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from db.deps import get_db
from db.models import Base
from db.models.expediente import Expediente
from db.models.etapa_respuesta import EtapaRespuesta
from db.models.tipo_medida import TipoMedida
from db.models.municipio import Municipio
from db.models.vereda import Vereda
from db.models.expediente_involucrado import ExpedienteInvolucrado
from db.models.informe_tecnico import InformeTecnico
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
    transport = ASGITransport(app=main_module.app)
    # base_url sin prefijo: cada test usa la ruta completa ("/etapas/...", "/expedientes/...").
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    main_module.app.dependency_overrides.clear()


def gateway_headers(user_id: int, rol_id: int = 1) -> dict:
    return {
        "x-gateway-token": os.environ["SECRET_GATEWAY"],
        "X-Gateway-User-Id": str(user_id),
        "X-Gateway-Role-Id": str(rol_id),
    }


@pytest.fixture
def permiso_consulta(monkeypatch):
    """El usuario de la petición tiene infraccion_consultar (lecturas de
    expediente: services.etapas.exigir_lectura_expediente)."""
    import services.etapas as etapas_mod

    async def _verify(user_id, permission):
        return permission == "infraccion_consultar"

    monkeypatch.setattr(etapas_mod, "verify_permission", _verify)


@pytest_asyncio.fixture
async def make_expediente(db_session):
    async def _make(abogado_responsable_id: int = 1, **overrides) -> Expediente:
        n = next(_radicado_counter)
        defaults = dict(
            radicado=f"TEST-{n:06d}",
            abogado_responsable_id=abogado_responsable_id,
            direccion="Vereda de prueba",
        )
        defaults.update(overrides)
        exp = Expediente(**defaults)
        db_session.add(exp)
        await db_session.flush()
        return exp

    return _make


@pytest_asyncio.fixture
async def make_etapa_respuesta(db_session):
    async def _make(expediente_id: int, **overrides) -> EtapaRespuesta:
        n = next(_radicado_counter)
        defaults = dict(
            expediente_id=expediente_id,
            radicado=f"2024EE{n:04d}",
            fecha_radicado=date(2024, 1, 10),
            fecha_creacion=date(2024, 1, 10),
            requiere_medida_preventiva=False,
        )
        defaults.update(overrides)
        etapa = EtapaRespuesta(**defaults)
        db_session.add(etapa)
        await db_session.flush()
        return etapa

    return _make


@pytest_asyncio.fixture
async def tipo_medida(db_session) -> TipoMedida:
    tipo = TipoMedida(nombre="Decomiso")
    db_session.add(tipo)
    await db_session.flush()
    return tipo


@pytest_asyncio.fixture
async def make_municipio_vereda(db_session):
    async def _make(municipio_nombre: str = "Chivor", vereda_nombre: str = "Centro"):
        muni = Municipio(nombre=municipio_nombre)
        db_session.add(muni)
        await db_session.flush()
        vereda = Vereda(nombre=vereda_nombre, municipio_id=muni.id)
        db_session.add(vereda)
        await db_session.flush()
        return muni, vereda

    return _make


@pytest_asyncio.fixture
async def make_informe_visita_aceptado(db_session):
    async def _make(expediente_id: int) -> InformeTecnico:
        informe = InformeTecnico(
            expediente_id=expediente_id,
            tipo_informe="VISITA",
            fecha_aceptacion_informe=date(2024, 1, 15),
        )
        db_session.add(informe)
        await db_session.flush()
        return informe

    return _make


@pytest_asyncio.fixture
async def link_involucrado(db_session):
    async def _make(expediente_id: int, involucrado_id: int) -> ExpedienteInvolucrado:
        link = ExpedienteInvolucrado(expediente_id=expediente_id, involucrado_id=involucrado_id)
        db_session.add(link)
        await db_session.flush()
        return link

    return _make


# ─── Stubs de FilesClient / UsersClient (proceso de revisión de informes) ────

class FilesClientStub:
    """Sustituye a satc_shared FilesClient: upload/usage/download en memoria."""

    def __init__(self):
        self._siguiente = 100
        self.contenidos: dict[int, tuple[bytes, str]] = {}
        self.subidos: list[str] = []
        self.incrementados: list[int] = []
        self.decrementados: list[int] = []

    async def upload(self, filename, content, content_type="application/octet-stream", *, timeout=60.0):
        from satc_shared.clients import UploadResult

        self._siguiente += 1
        fid = self._siguiente
        self.contenidos[fid] = (content, content_type)
        self.subidos.append(filename)
        return UploadResult(ok=True, file_id=fid, file_url=f"/files/{fid}", file_hash=f"hash{fid}")

    async def increment_usage(self, file_ids):
        from satc_shared.clients import UsageResult

        self.incrementados.extend(file_ids)
        return UsageResult(ok=True)

    async def decrement_usage(self, file_ids):
        from satc_shared.clients import UsageResult

        self.decrementados.extend(file_ids)
        return UsageResult(ok=True)

    def download(self, file_id, *, timeout=120.0):
        from contextlib import asynccontextmanager

        import httpx
        from satc_shared.clients import NotFoundError

        @asynccontextmanager
        async def _cm():
            if file_id not in self.contenidos:
                raise NotFoundError("no existe", service="app-docs", status_code=404)
            content, ctype = self.contenidos[file_id]
            yield httpx.Response(200, content=content, headers={"content-type": ctype})

        return _cm()


class UsersClientStub:
    def __init__(self):
        self.notificaciones: list[dict] = []

    async def create_notification(self, notification=None, *, timeout=5.0, **fields):
        self.notificaciones.append(fields)

    def para(self, usuario_id: int) -> list[str]:
        return [n["mensaje"] for n in self.notificaciones if n["usuario_id"] == usuario_id]


@pytest_asyncio.fixture
async def stubs_clientes(monkeypatch):
    """Sustituye los clientes inter-servicio por stubs en memoria."""
    import types

    import services.docs as docs_svc
    import services.notification as notif_svc
    import services.users as users_svc

    files = FilesClientStub()
    users = UsersClientStub()
    monkeypatch.setattr(docs_svc, "files_client", files)
    monkeypatch.setattr(notif_svc, "users_client", users)

    async def _get_user_info(ids):
        return {i: {"nombre": f"Usuario {i}", "correo": "", "numero_documento": ""} for i in ids}

    monkeypatch.setattr(users_svc, "get_user_info", _get_user_info)
    return types.SimpleNamespace(files=files, users=users)
