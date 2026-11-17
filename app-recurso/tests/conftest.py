"""Fixtures compartidas de app-recurso (patrón de app-infraction/tests/conftest.py).

Base de datos
-------------
Postgres real y separado: ``TEST_DATABASE_URL`` (default
``postgres-recurso:5432/recurso_test_db``, como el resto de servicios en
Docker). En esta máquina (DISENO_TECNICO §7)::

    TEST_DATABASE_URL='postgresql+asyncpg://postgres:Satc2026%23Secure@127.0.0.1:55432/recurso_test_db' \
        ../.venv/Scripts/python.exe -m pytest -q

- El esquema se crea una vez por sesión (``create_all``) y los catálogos
  (municipios, veredas, tipo_fuente, fuente, tipo_notificacion) se cargan con
  el seed real (``db/seeds.py``) una sola vez.
- Al terminar cada test se hace TRUNCATE de todas las tablas **excepto** los
  catálogos (``TABLAS_CATALOGO``).
- Cada petición HTTP abre su PROPIA sesión (igual que ``get_db`` en
  producción). Por eso las fábricas de datos hacen ``commit``, y se pueden
  lanzar peticiones concurrentes (``asyncio.gather``) para probar 409.

Servicios externos (autouse, ningún test sale a la red)
-------------------------------------------------------
``stubs`` sustituye los clientes de ``satc_shared`` en ``services/*``:

- ``stubs.permisos``: permisos por usuario. ``services.users.verify_permission``
  (y por tanto ``core.acceso``) responde según lo que se le dé aquí.
  ``stubs.permisos.dar(user_id, *slugs)``; ``quitar(user_id)``. Limpia la caché
  de permisos de ``utils/cache.py`` en cada cambio.
  ``users_by_permission`` devuelve los usuarios con ese permiso;
  ``users_batch`` devuelve "Usuario {id}".
- ``stubs.users.notificaciones``: notificaciones creadas (``create_notification``).
  ``stubs.users.para(user_id)`` -> mensajes de ese usuario.
- ``stubs.files``: app-docs en memoria. ``stubs.files.registrar(content=b"%PDF..",
  content_type="application/pdf") -> file_id`` simula un archivo ya subido;
  ``incrementados`` / ``decrementados`` / ``unificados`` registran llamadas;
  ``fallar_incremento = True`` simula fallo de app-docs.
- ``stubs.involved``: app-involved en memoria.
  ``stubs.involved.registrar(id, nombre=..., tipo_documento="CC"|"NIT", ...)``;
  ``caido = True`` simula app-involved sin responder.

Fixtures de uso común
---------------------
- ``client``: ``httpx.AsyncClient`` contra la app (rutas sin prefijo
  ``/recurso``: ``/expedientes``, ``/involucrados``, ...).
- ``gateway_headers(user_id, rol_id=1)``: headers que inyecta el gateway.
- ``como(user_id, *permisos) -> headers``: da los permisos y devuelve los
  headers. Ej: ``h = como(GESTOR, Permission.MANAGE)``.
  Usuarios predefinidos: ``GESTOR`` (10), ``CONSULTOR`` (11), ``SUPER`` (12),
  ``SIN_PERMISOS`` (13) — constantes importables de ``tests.conftest``.
- ``h_gestor`` / ``h_consultor`` / ``h_super`` / ``h_sin_permisos``: headers ya
  listos con ``recurso_gestionar`` / ``recurso_consultar`` /
  ``recurso_super_gestion`` / nada.
- ``catalogo``: ids reales del seed: ``catalogo.vereda_id``,
  ``catalogo.municipio_id``, ``catalogo.otra_vereda_id`` (otro municipio),
  ``catalogo.tipo_fuente_id``, ``catalogo.fuente_ids`` (dos fuentes),
  ``catalogo.tipo_notificacion_ids`` ({nombre: id}).
- ``payload_expediente(**overrides) -> dict``: body válido para
  ``POST /expedientes`` (registra el comprobante en ``stubs.files``).
- ``crear_expediente(**overrides) -> Expediente``: inserta directo en la BD
  (con fuentes y usos) y hace commit. Overrides aceptados: cualquier columna
  de ``expediente`` + ``fuente_ids`` + ``usos``.
- ``vincular(expediente_id, involucrado_id, tipo_vinculo=SOLICITANTE,
  representante_id=None, **cols) -> ExpedienteInvolucrado``: inserta el
  vínculo directo en la BD (commit) y registra a la persona en
  ``stubs.involved`` si no existía.
- ``db_session``: sesión para preparar/verificar datos (hacer ``commit`` o
  ``refresh`` según el caso; usa ``expire_on_commit=False``).
"""
import os

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:Satc2026#Secure@postgres-recurso:5432/recurso_test_db",
)
# db/database.py crea su engine al importarse con DATABASE_URL: se apunta a la
# BD de pruebas (lo usa solo el seed de catálogos de la sesión).
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("SECRET_GATEWAY", "test-gateway-secret")
os.environ.setdefault("SERVICE_SECRET_KEY", "test-service-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

import itertools
import types
from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.permission import Permission
from db.deps import get_db
from db.models import (
    Base,
    Expediente,
    ExpedienteFuente,
    ExpedienteInvolucrado,
    ExpedienteUso,
    Fuente,
    TipoFuente,
    TipoNotificacion,
    TipoVinculo,
    UsoAgua,
    Vereda,
)
import main as main_module

engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

TABLAS_CATALOGO = ("municipio", "vereda", "tipo_fuente", "fuente", "tipo_notificacion")

GESTOR = 10
CONSULTOR = 11
SUPER = 12
SIN_PERMISOS = 13

_contador = itertools.count(1)


# ─── Base de datos ───────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def _crear_esquema():
    from db.migrations import aplicar_migraciones

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # La BD de pruebas persiste entre corridas: create_all no agrega
        # columnas nuevas a tablas existentes (igual que en producción).
        await aplicar_migraciones(conn)
    # Catálogos reales (seed idempotente de la app) una sola vez por sesión.
    import db.database as app_db
    from db.seeds import seed_initial_data

    await seed_initial_data()
    await app_db.engine.dispose()
    yield
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def _limpiar_tablas():
    yield
    async with engine.begin() as conn:
        tablas = (await conn.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ))).scalars().all()
        tablas = [t for t in tablas if t not in TABLAS_CATALOGO]
        if tablas:
            await conn.execute(text(
                f'TRUNCATE TABLE {", ".join(tablas)} RESTART IDENTITY CASCADE'
            ))


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    async def _override_get_db():
        # Una sesión por petición (como producción): permite concurrencia real.
        async with TestSessionLocal() as session:
            yield session

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


# ─── Stubs de servicios externos ─────────────────────────────────────────────

class Permisos:
    """Registro user_id -> permisos que consulta el stub de UsersClient."""

    def __init__(self):
        self._por_usuario: dict[int, set[str]] = {}

    def _limpiar_cache(self) -> None:
        from utils.cache import permission_cache, users_cache

        permission_cache.cache.clear()
        users_cache.cache.clear()

    def dar(self, user_id: int, *permisos: str) -> None:
        self._por_usuario.setdefault(user_id, set()).update(permisos)
        self._limpiar_cache()

    def quitar(self, user_id: int, *permisos: str) -> None:
        if permisos:
            self._por_usuario.get(user_id, set()).difference_update(permisos)
        else:
            self._por_usuario.pop(user_id, None)
        self._limpiar_cache()

    def tiene(self, user_id: int, permiso: str) -> bool:
        return permiso in self._por_usuario.get(user_id, set())

    def usuarios_con(self, permiso: str) -> list[int]:
        return sorted(u for u, p in self._por_usuario.items() if permiso in p)


class UsersClientStub:
    def __init__(self, permisos: Permisos):
        self.permisos = permisos
        self.notificaciones: list[dict] = []

    async def verify_permission(self, user_id, permission):
        return self.permisos.tiene(user_id, permission)

    async def users_by_permission(self, permission):
        from satc_shared.clients import UserInfo

        return [
            UserInfo(id=u, nombre=f"Usuario {u}", correo=f"u{u}@test.local", numero_documento=str(1000 + u))
            for u in self.permisos.usuarios_con(permission)
        ]

    async def users_batch(self, user_ids):
        from satc_shared.clients import UserInfo

        return [
            UserInfo(id=u, nombre=f"Usuario {u}", correo=f"u{u}@test.local", numero_documento=str(1000 + u))
            for u in user_ids
        ]

    async def create_notification(self, notification=None, *, timeout=5.0, **fields):
        if notification is not None:
            fields = notification.model_dump()
        self.notificaciones.append(fields)

    def para(self, usuario_id: int) -> list[str]:
        return [n["mensaje"] for n in self.notificaciones if n["usuario_id"] == usuario_id]


class FilesClientStub:
    """app-docs en memoria (copia del stub de app-infraction)."""

    def __init__(self):
        self._siguiente = 100
        self.contenidos: dict[int, tuple[bytes, str]] = {}
        self.subidos: list[str] = []
        self.incrementados: list[int] = []
        self.decrementados: list[int] = []
        self.unificados: list[list[int]] = []
        self.fallar_incremento = False

    def registrar(self, content: bytes = b"%PDF-1.4", content_type: str = "application/pdf") -> int:
        """Simula un archivo ya subido a app-docs; devuelve su id."""
        self._siguiente += 1
        self.contenidos[self._siguiente] = (content, content_type)
        return self._siguiente

    async def get(self, file_id):
        from satc_shared.clients import FileInfo, NotFoundError

        if file_id not in self.contenidos:
            raise NotFoundError("no existe", service="app-docs", status_code=404)
        content, ctype = self.contenidos[file_id]
        return FileInfo(id=file_id, file_url=f"/files/{file_id}", content_type=ctype, file_size=len(content))

    async def batch(self, file_ids):
        return [await self.get(f) for f in file_ids if f in self.contenidos]

    async def download_unified(self, file_ids, *, cookies=None, timeout=120.0):
        self.unificados.append(list(file_ids))
        return b"%PDF-unificado"

    async def upload(self, filename, content, content_type="application/octet-stream", *, timeout=60.0):
        from satc_shared.clients import UploadResult

        self._siguiente += 1
        fid = self._siguiente
        self.contenidos[fid] = (content, content_type)
        self.subidos.append(filename)
        return UploadResult(ok=True, file_id=fid, file_url=f"/files/{fid}", file_hash=f"hash{fid}")

    async def increment_usage(self, file_ids):
        from satc_shared.clients import ServiceClientError, UsageResult

        if self.fallar_incremento:
            raise ServiceClientError("app-docs caído", service="app-docs", status_code=503)
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


class InvolvedClientStub:
    """app-involved en memoria (endpoint /bulk)."""

    def __init__(self):
        self.personas: dict[int, dict] = {}
        self.caido = False

    def registrar(
        self,
        id: int,
        nombre: str | None = None,
        tipo_documento: str = "CC",
        numero_documento: int | None = None,
        digito_verificacion: str | None = None,
    ) -> dict:
        persona = {
            "id": id,
            "numero_documento": numero_documento or 1_000_000 + id,
            "digito_verificacion": digito_verificacion,
            "tipo_documento": tipo_documento,
            "nombre": nombre or f"Persona {id}",
            "celular": None,
            "correo": None,
            "direccion": None,
        }
        self.personas[id] = persona
        return persona

    async def bulk(self, ids):
        if self.caido:
            from satc_shared.clients import ServiceClientError

            raise ServiceClientError("app-involved caído", service="app-involved", status_code=503)
        return [dict(self.personas[i]) for i in ids if i in self.personas]


@pytest.fixture(autouse=True)
def stubs(monkeypatch):
    """Sustituye users/docs/involved/notification por stubs en memoria (autouse)."""
    import services.docs as docs_svc
    import services.involved as involved_svc
    import services.notification as notif_svc
    import services.users as users_svc

    permisos = Permisos()
    users = UsersClientStub(permisos)
    files = FilesClientStub()
    involved = InvolvedClientStub()
    monkeypatch.setattr(users_svc, "users_client", users)
    monkeypatch.setattr(notif_svc, "users_client", users)
    monkeypatch.setattr(docs_svc, "files_client", files)
    monkeypatch.setattr(involved_svc, "involved_client", involved)
    permisos._limpiar_cache()
    yield types.SimpleNamespace(permisos=permisos, users=users, files=files, involved=involved)
    permisos._limpiar_cache()


@pytest.fixture
def como(stubs):
    def _como(user_id: int, *permisos: str) -> dict:
        stubs.permisos.dar(user_id, *permisos)
        return gateway_headers(user_id)

    return _como


@pytest.fixture
def h_gestor(como):
    return como(GESTOR, Permission.MANAGE)


@pytest.fixture
def h_consultor(como):
    return como(CONSULTOR, Permission.CONSULT)


@pytest.fixture
def h_super(como):
    return como(SUPER, Permission.SUPER_MANAGE)


@pytest.fixture
def h_sin_permisos():
    return gateway_headers(SIN_PERMISOS)


# ─── Datos ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def catalogo(db_session):
    veredas = (await db_session.execute(select(Vereda).order_by(Vereda.id))).scalars().all()
    vereda = veredas[0]
    otra = next(v for v in veredas if v.municipio_id != vereda.municipio_id)
    tipo_fuente_id = await db_session.scalar(select(TipoFuente.id).order_by(TipoFuente.id))
    fuente_ids = (await db_session.execute(select(Fuente.id).order_by(Fuente.id).limit(2))).scalars().all()
    tipos_notif = {t.nombre: t.id for t in (await db_session.execute(select(TipoNotificacion))).scalars()}
    return types.SimpleNamespace(
        vereda_id=vereda.id,
        municipio_id=vereda.municipio_id,
        otra_vereda_id=otra.id,
        otro_municipio_id=otra.municipio_id,
        tipo_fuente_id=tipo_fuente_id,
        fuente_ids=list(fuente_ids),
        tipo_notificacion_ids=tipos_notif,
    )


@pytest.fixture
def payload_expediente(catalogo, stubs):
    def _payload(**overrides) -> dict:
        n = next(_contador)
        datos = {
            "radicado": f"2026ER{n:05d}",
            "fecha_radicado": "2026-03-10",
            "expediente": f"CA {n:03d}-26",
            "numero_vital": f"VITAL-{n}",
            "nombre_predio": "La Esperanza",
            "matricula_inmobiliaria": "078-12345",
            "codigo_catastral": "15001000100020003",
            "radicado_oficio_entrada": f"2026ER9{n:04d}",
            "fecha_oficio_entrada": "2026-03-01",
            "doc_comprobante_pago_id": stubs.files.registrar(),
            "vereda_id": catalogo.vereda_id,
            "tipo_fuente_id": catalogo.tipo_fuente_id,
            "nombre_fuente": "Juancho Castro",
            "fuente_ids": catalogo.fuente_ids[:1],
            "usos": ["DOMESTICO"],
        }
        datos.update(overrides)
        return datos

    return _payload


@pytest_asyncio.fixture
async def crear_expediente(db_session, catalogo, stubs):
    async def _crear(**overrides) -> Expediente:
        n = next(_contador)
        fuente_ids = overrides.pop("fuente_ids", catalogo.fuente_ids[:1])
        usos = overrides.pop("usos", [UsoAgua.DOMESTICO])
        datos = dict(
            radicado=f"2026ER{n:05d}",
            fecha_radicado=date(2026, 3, 10),
            expediente=f"CA {n:03d}-26",
            numero_vital=f"VITAL-{n}",
            nombre_predio="La Esperanza",
            matricula_inmobiliaria="078-12345",
            codigo_catastral="15001000100020003",
            radicado_oficio_entrada=f"2026ER9{n:04d}",
            fecha_oficio_entrada=date(2026, 3, 1),
            doc_comprobante_pago_id=stubs.files.registrar(),
            vereda_id=catalogo.vereda_id,
            tipo_fuente_id=catalogo.tipo_fuente_id,
            nombre_fuente="Juancho Castro",
        )
        datos.update(overrides)
        expediente = Expediente(**datos)
        db_session.add(expediente)
        await db_session.flush()
        db_session.add_all(
            [ExpedienteFuente(expediente_id=expediente.id, fuente_id=f) for f in fuente_ids]
            + [ExpedienteUso(expediente_id=expediente.id, uso=UsoAgua(u)) for u in usos]
        )
        await db_session.commit()
        return expediente

    return _crear


@pytest_asyncio.fixture
async def vincular(db_session, stubs):
    async def _vincular(
        expediente_id: int,
        involucrado_id: int,
        tipo_vinculo: TipoVinculo = TipoVinculo.SOLICITANTE,
        representante_id: int | None = None,
        **cols,
    ) -> ExpedienteInvolucrado:
        if involucrado_id not in stubs.involved.personas:
            stubs.involved.registrar(involucrado_id)
        if representante_id and representante_id not in stubs.involved.personas:
            stubs.involved.registrar(representante_id)
        vinculo = ExpedienteInvolucrado(
            expediente_id=expediente_id,
            involucrado_id=involucrado_id,
            tipo_vinculo=tipo_vinculo,
            representante_id=representante_id,
            **cols,
        )
        db_session.add(vinculo)
        await db_session.commit()
        return vinculo

    return _vincular
