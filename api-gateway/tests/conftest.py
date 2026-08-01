"""Fixtures del gateway.

El gateway no tiene base de datos: sus únicas dependencias externas son los
microservicios (vía `main.http_client`) y Redis. Ambas se sustituyen acá por
dobles controlados para poder afirmar exactamente QUÉ cabeceras y QUÉ URL
termina recibiendo el microservicio destino — que es lo que la auditoría de
seguridad necesita verificar.
"""
import json
import os
import time
import uuid

import httpx
import pytest
import pytest_asyncio

os.environ.setdefault("SECRET_GATEWAY", "gateway-secret-de-test")
os.environ.setdefault("SECRET_KEY_GATEWAY", "0123456789abcdef0123456789abcdef")

import main  # noqa: E402
from utils import funciones  # noqa: E402

SECRET_KEY_GATEWAY = os.environ["SECRET_KEY_GATEWAY"]


class PeticionCapturada:
    """Guarda la última petición que el gateway envió al microservicio."""

    def __init__(self):
        self.request: httpx.Request | None = None

    @property
    def headers(self) -> httpx.Headers:
        assert self.request is not None, "el gateway no reenvió ninguna petición"
        return self.request.headers

    @property
    def url(self) -> httpx.URL:
        assert self.request is not None, "el gateway no reenvió ninguna petición"
        return self.request.url


@pytest.fixture
def upstream(monkeypatch):
    captura = PeticionCapturada()

    def handler(request: httpx.Request) -> httpx.Response:
        captura.request = request
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(
        main, "http_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    return captura


class PipelineFalso:
    """Acumula comandos y los ejecuta en orden, como el pipeline de redis-py."""

    def __init__(self, redis):
        self.redis = redis
        self.comandos = []

    def incr(self, key):
        self.comandos.append(("incr", key))
        return self

    def ttl(self, key):
        self.comandos.append(("ttl", key))
        return self

    async def execute(self):
        resultados = []
        for op, key in self.comandos:
            if op == "incr":
                resultados.append(await self.redis.incr(key))
            elif op == "ttl":
                resultados.append(await self.redis.ttl(key))
        self.comandos = []
        return resultados


class RedisFalso:
    """Doble con estado: los contadores del rate limiter deben sobrevivir entre
    peticiones del mismo test, igual que en el Redis real."""

    def __init__(self, valores=None):
        self.valores = valores or {}
        self.ttls = {}

    async def get(self, key):
        return self.valores.get(key)

    async def incr(self, key):
        self.valores[key] = int(self.valores.get(key, 0)) + 1
        return self.valores[key]

    async def ttl(self, key):
        return self.ttls.get(key, -1)

    async def expire(self, key, segundos):
        self.ttls[key] = segundos
        return True

    def pipeline(self):
        return PipelineFalso(self)


@pytest.fixture
def redis_con(monkeypatch):
    """Devuelve una función para fijar el contenido de Redis en el test.

    La instancia es única por test (no una nueva por llamada) para que los
    contadores del rate limiter se acumulen entre peticiones.
    """

    def _set(valores):
        fake = RedisFalso(valores)
        monkeypatch.setattr(main, "get_redis_client", lambda: fake)
        return fake

    return _set


@pytest.fixture(autouse=True)
def redis_vacio(monkeypatch):
    fake = RedisFalso()
    monkeypatch.setattr(main, "get_redis_client", lambda: fake)
    return fake


@pytest.fixture(autouse=True)
def circuito_limpio():
    funciones.CIRCUIT_BREAKER.clear()
    yield
    funciones.CIRCUIT_BREAKER.clear()


def crear_token(user_id="1", rol_id=1, jti=None, exp_delta=600):
    from jose import jwe

    jti = jti or str(uuid.uuid4())
    ahora = int(time.time())
    payload = {
        "sub": str(user_id),
        "rol_id": rol_id,
        "jti": jti,
        "iat": ahora,
        "exp": ahora + exp_delta,
    }
    token = jwe.encrypt(
        plaintext=json.dumps(payload).encode("utf-8"),
        key=SECRET_KEY_GATEWAY,
        algorithm="dir",
        encryption="A256GCM",
    ).decode("utf-8")
    return token, jti


@pytest_asyncio.fixture
async def cliente():
    transport = httpx.ASGITransport(app=main.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def peticion_asgi():
    """Invoca la app ASGI con el path tal cual, sin pasar por httpx.

    httpx colapsa los segmentos `.`/`..` del lado del cliente, así que es el
    único modo de probar que el gateway rechaza un path con traversal.
    """

    async def _peticion(path: str, method: str = "GET", cookie: str | None = None):
        ruta, _, query = path.partition("?")
        headers = [(b"host", b"test")]
        if cookie:
            headers.append((b"cookie", cookie.encode()))
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.1"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": ruta,
            "raw_path": ruta.encode(),
            "query_string": query.encode(),
            "headers": headers,
            "client": ("127.0.0.1", 12345),
            "server": ("test", 80),
            "root_path": "",
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        respuesta = {"status": None, "body": b""}

        async def send(message):
            if message["type"] == "http.response.start":
                respuesta["status"] = message["status"]
            elif message["type"] == "http.response.body":
                respuesta["body"] += message.get("body", b"")

        await main.app(scope, receive, send)
        return respuesta["status"], respuesta["body"]

    return _peticion


@pytest_asyncio.fixture
async def cliente_autenticado(cliente, redis_con):
    """Cliente con una sesión válida ya registrada en Redis."""
    token, jti = crear_token()
    redis_con({"session:user:1": jti})
    cliente.cookies.set("access_token", token)
    return cliente
