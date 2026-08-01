"""Proxy genérico: enrutado, validación de path y propagación de la petición."""
import httpx
import pytest

import main
from utils import funciones


async def test_servicio_desconocido_da_404(cliente, upstream):
    r = await cliente.get("/inexistente/algo")
    assert r.status_code == 404
    assert upstream.request is None


@pytest.mark.parametrize("servicio", list(main.MICROSERVICES))
async def test_cada_servicio_enruta_a_su_host(servicio, cliente_autenticado, upstream):
    await cliente_autenticado.get(f"/{servicio}/recurso/1")
    assert str(upstream.url) == f"{main.MICROSERVICES[servicio]}/recurso/1"


async def test_query_string_se_propaga(cliente_autenticado, upstream):
    await cliente_autenticado.get("/users/recurso?page=2&q=hola")
    assert upstream.url.params["page"] == "2"
    assert upstream.url.params["q"] == "hola"


async def test_body_se_propaga(cliente_autenticado, upstream):
    await cliente_autenticado.post("/users/recurso", json={"a": 1})
    assert upstream.request.content == b'{"a":1}'


async def test_status_y_body_del_backend_se_devuelven(cliente_autenticado, monkeypatch):
    def handler(request):
        return httpx.Response(418, json={"detalle": "soy una tetera"})

    monkeypatch.setattr(
        main, "http_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    r = await cliente_autenticado.get("/users/recurso")
    assert r.status_code == 418
    assert r.json() == {"detalle": "soy una tetera"}


# ── Path traversal ──────────────────────────────────────────────────────────
# httpx colapsa los segmentos punto al construir la URL destino, así que un
# `..` permite partir de un prefijo de PUBLIC_ROUTES y alcanzar cualquier
# endpoint protegido sin sesión. El gateway debe rechazarlo antes de proxear.
#
# El path va por ASGI crudo: httpx normaliza los segmentos punto del lado del
# cliente, así que un `cliente.get(".../..")` nunca llegaría con el `..` puesto.
@pytest.mark.parametrize(
    "path",
    [
        "/users/health/../user/all",
        "/users/auth/login/../../user/all",
        "/users/a/./b",
        "/users/../otro-servicio",
    ],
)
async def test_traversal_rechazado(path, upstream, peticion_asgi):
    status, _ = await peticion_asgi(path)
    assert status == 400
    assert upstream.request is None, "el gateway proxeó un path con traversal"


async def test_traversal_rechazado_aun_con_sesion_valida(
    upstream, peticion_asgi, redis_con
):
    from conftest import crear_token

    token, jti = crear_token()
    redis_con({"session:user:1": jti})
    status, _ = await peticion_asgi(
        "/users/health/../user/all", cookie=f"access_token={token}"
    )
    assert status == 400
    assert upstream.request is None


async def test_path_normal_no_se_confunde_con_traversal(cliente_autenticado, upstream):
    """Un `..` dentro de un segmento (no como segmento entero) es legítimo."""
    r = await cliente_autenticado.get("/users/archivo..pdf")
    assert r.status_code == 200


# ── Redirects del backend ───────────────────────────────────────────────────
# El gateway pone `X-Gateway-Token` en cada petición al backend. Con
# `follow_redirects=True`, un microservicio comprometido puede devolver un 3xx
# a un host externo y hacer que el gateway repita la petición allí *con el
# token*, filtrando el secreto que lo autentica ante todos los servicios.


def _cliente_que_redirige(destino, status=307):
    def handler(request):
        if str(request.url).startswith("http://evil.example.com"):
            return httpx.Response(200, json={"robado": True})
        return httpx.Response(status, headers={"Location": destino})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_gateway_no_sigue_redirects_del_backend(cliente_autenticado, monkeypatch):
    monkeypatch.setattr(
        main, "http_client", _cliente_que_redirige("http://evil.example.com/robar")
    )
    r = await cliente_autenticado.get("/users/recurso")
    assert r.status_code == 307, "el gateway siguió el redirect"
    assert b"robado" not in r.content


async def test_redirect_externo_pierde_la_cabecera_location(
    cliente_autenticado, monkeypatch
):
    """Un servicio interno mandando al cliente afuera es anómalo: se descarta."""
    monkeypatch.setattr(
        main, "http_client", _cliente_que_redirige("http://evil.example.com/robar")
    )
    r = await cliente_autenticado.get("/users/recurso")
    assert "location" not in {k.lower() for k in r.headers}


async def test_no_se_filtra_el_token_del_gateway_al_destino_del_redirect(
    cliente_autenticado, monkeypatch
):
    vistos = []

    def handler(request):
        vistos.append(str(request.url))
        if "evil" in str(request.url):
            return httpx.Response(200)
        return httpx.Response(302, headers={"Location": "http://evil.example.com/x"})

    monkeypatch.setattr(
        main, "http_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    await cliente_autenticado.get("/users/recurso")
    assert not any("evil" in u for u in vistos), (
        "el gateway contactó el destino externo llevándose X-Gateway-Token"
    )


async def test_redirect_interno_se_reescribe_a_ruta_del_gateway(
    cliente_autenticado, monkeypatch
):
    """El `Location` a un host de la red privada no lo puede resolver el
    navegador y además revela la topología interna."""
    monkeypatch.setattr(
        main,
        "http_client",
        _cliente_que_redirige(f"{main.MICROSERVICES['users']}/otro/recurso"),
    )
    r = await cliente_autenticado.get("/users/recurso")
    assert r.headers["location"] == "/users/otro/recurso"
    assert "app-users" not in r.headers["location"]


async def test_redirect_relativo_se_prefija_con_el_servicio(
    cliente_autenticado, monkeypatch
):
    monkeypatch.setattr(main, "http_client", _cliente_que_redirige("/otro/recurso"))
    r = await cliente_autenticado.get("/users/recurso")
    assert r.headers["location"] == "/users/otro/recurso"


async def test_respuesta_normal_no_se_toca(cliente_autenticado, monkeypatch):
    def handler(request):
        return httpx.Response(200, headers={"Location": "/no-tocar"}, json={"ok": True})

    monkeypatch.setattr(
        main, "http_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    r = await cliente_autenticado.get("/users/recurso")
    assert r.headers["location"] == "/no-tocar"


def test_clientes_httpx_no_siguen_redirects():
    assert main.http_client.follow_redirects is False


# ── Fallos del upstream ─────────────────────────────────────────────────────

async def test_timeout_del_backend_da_504(cliente_autenticado, monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)

    monkeypatch.setattr(
        main, "http_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    r = await cliente_autenticado.get("/users/recurso")
    assert r.status_code == 504
    assert r.json()["detail"] == "Gateway timeout"


async def test_error_de_red_da_503_sin_filtrar_detalle_interno(cliente_autenticado, monkeypatch):
    def handler(request):
        raise httpx.ConnectError("connection refused a app-users:8001", request=request)

    monkeypatch.setattr(
        main, "http_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    r = await cliente_autenticado.get("/users/recurso")
    assert r.status_code == 503
    assert r.json()["detail"] == "Service unavailable"
    assert "app-users" not in r.text, "se filtró el host interno al cliente"


async def test_circuit_breaker_abre_tras_fallos_repetidos(cliente_autenticado, monkeypatch):
    def handler(request):
        raise httpx.ConnectError("caido", request=request)

    monkeypatch.setattr(
        main, "http_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    for _ in range(funciones.CIRCUIT_BREAKER_THRESHOLD):
        await cliente_autenticado.get("/users/recurso")

    r = await cliente_autenticado.get("/users/recurso")
    assert r.status_code == 503
    assert "temporarily unavailable" in r.json()["detail"]


# ── Health ──────────────────────────────────────────────────────────────────

async def test_health_no_requiere_sesion(cliente):
    r = await cliente.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
    assert set(r.json()["services"]) == set(main.MICROSERVICES)
