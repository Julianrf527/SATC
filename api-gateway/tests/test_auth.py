"""Autenticación de usuario, sesión en Redis y rutas públicas."""
import pytest

import main
from conftest import crear_token


# ── Sin sesión ──────────────────────────────────────────────────────────────

async def test_ruta_protegida_sin_cookie_da_401(cliente, upstream):
    r = await cliente.get("/users/user/all")
    assert r.status_code == 401
    assert upstream.request is None


async def test_token_ilegible_da_401(cliente, upstream):
    cliente.cookies.set("access_token", "basura")
    r = await cliente.get("/users/user/all")
    assert r.status_code == 401
    assert upstream.request is None
    cliente.cookies.clear()


async def test_token_sin_claims_obligatorias_da_401(cliente, upstream):
    import json

    from jose import jwe

    from conftest import SECRET_KEY_GATEWAY

    token = jwe.encrypt(
        plaintext=json.dumps({"sub": "1"}).encode(),
        key=SECRET_KEY_GATEWAY,
        algorithm="dir",
        encryption="A256GCM",
    ).decode()
    cliente.cookies.set("access_token", token)
    r = await cliente.get("/users/user/all")
    assert r.status_code == 401
    assert upstream.request is None
    cliente.cookies.clear()


async def test_token_expirado_da_401(cliente, redis_con, upstream):
    """`jwe.decrypt` no valida claims: la expiración se comprueba a mano."""
    token, jti = crear_token(exp_delta=-10)
    redis_con({"session:user:1": jti})
    cliente.cookies.set("access_token", token)
    r = await cliente.get("/users/user/all")
    assert r.status_code == 401
    assert r.json()["detail"] == "Token expirado"
    assert upstream.request is None
    cliente.cookies.clear()


# ── Sesión en Redis ─────────────────────────────────────────────────────────

async def test_sesion_ausente_en_redis_da_401(cliente, upstream):
    """Fail-closed: el logout borra la clave, así que su ausencia invalida."""
    token, _ = crear_token()
    cliente.cookies.set("access_token", token)
    r = await cliente.get("/users/user/all")
    assert r.status_code == 401
    assert r.json()["detail"] == "session_expired"
    assert upstream.request is None
    cliente.cookies.clear()


async def test_jti_distinto_da_401(cliente, redis_con, upstream):
    token, _ = crear_token()
    redis_con({"session:user:1": "otro-jti"})
    cliente.cookies.set("access_token", token)
    r = await cliente.get("/users/user/all")
    assert r.status_code == 401
    assert r.json()["detail"] == "session_replaced"
    assert upstream.request is None
    cliente.cookies.clear()


async def test_redis_caido_da_503_y_no_proxea(cliente, monkeypatch, upstream):
    token, _ = crear_token()
    monkeypatch.setattr(main, "get_redis_client", lambda: None)
    cliente.cookies.set("access_token", token)
    r = await cliente.get("/users/user/all")
    assert r.status_code == 503
    assert upstream.request is None
    cliente.cookies.clear()


async def test_sesion_valida_proxea_con_identidad(cliente_autenticado, upstream):
    r = await cliente_autenticado.get("/users/user/all")
    assert r.status_code == 200
    assert upstream.headers["X-Gateway-User-Id"] == "1"
    assert upstream.headers["X-Gateway-Role-Id"] == "1"


# ── Rutas públicas ──────────────────────────────────────────────────────────

RUTAS_PUBLICAS = sorted(
    (servicio, ruta)
    for servicio, rutas in main.PUBLIC_ROUTES.items()
    for ruta in rutas
)

RUTAS_COMUNES = sorted(
    (servicio, ruta)
    for servicio in main.MICROSERVICES
    for ruta in main.PUBLIC_ROUTES_COMUNES
)


@pytest.mark.parametrize("servicio,ruta", RUTAS_PUBLICAS)
async def test_ruta_publica_no_exige_sesion(servicio, ruta, cliente, upstream):
    r = await cliente.get(f"/{servicio}/{ruta}")
    assert r.status_code == 200
    assert upstream.request is not None


@pytest.mark.parametrize("servicio,ruta", RUTAS_COMUNES)
async def test_ruta_publica_comun_vale_en_todos_los_servicios(
    servicio, ruta, cliente, upstream
):
    """`health` lo expone cada microservicio; debe ser público en los cinco."""
    r = await cliente.get(f"/{servicio}/{ruta}")
    assert r.status_code == 200
    assert upstream.request is not None


# ── Scoping por servicio ────────────────────────────────────────────────────
# PUBLIC_ROUTES se indexa por servicio: si fuera un set global, una ruta
# pública de `documents` quedaría pública también en `users`, `infraction`,
# etc., y cualquier endpoint homónimo que se agregue allí sería un bypass de
# sesión silencioso.

@pytest.mark.parametrize(
    "servicio,ruta",
    [
        ("users", "files/increment-usage"),
        ("users", "files/decrement-usage"),
        ("users", "files/batch"),
        ("infraction", "auth/login"),
        ("documents", "auth/login"),
        ("sanctioning", "user/batch"),
        ("involveds", "email/send"),
        ("infraction", "role/verify"),
    ],
)
async def test_ruta_publica_de_otro_servicio_no_es_publica(
    servicio, ruta, cliente, upstream
):
    r = await cliente.get(f"/{servicio}/{ruta}")
    assert r.status_code == 401, (
        f"{ruta} es pública solo en otro servicio, no debería serlo en {servicio}"
    )
    assert upstream.request is None


async def test_ninguna_ruta_publica_vale_en_todos_los_servicios_por_accidente(
    cliente, upstream
):
    """Guardarraíl: si alguien vuelve a hacer global una ruta específica, salta."""
    for servicio, rutas in main.PUBLIC_ROUTES.items():
        for ruta in rutas:
            otros = [s for s in main.MICROSERVICES if s != servicio]
            for otro in otros:
                assert not main.es_ruta_publica(otro, ruta), (
                    f"{ruta} (de {servicio}) quedó pública también en {otro}"
                )


async def test_prefijo_publico_cubre_subrutas(cliente, upstream):
    r = await cliente.get("/users/user/permission/ver_expedientes")
    assert r.status_code == 200
    assert str(upstream.url).endswith("/user/permission/ver_expedientes")


async def test_ruta_publica_no_lleva_identidad_de_usuario(cliente, upstream):
    """Sin sesión no hay usuario que declarar; el destino debe exigir
    X-Service-Token para estos endpoints."""
    await cliente.post("/users/user/batch", json={"user_ids": [1]})
    assert "X-Gateway-User-Id" not in upstream.headers
    assert "X-Gateway-Role-Id" not in upstream.headers


async def test_ruta_no_listada_no_es_publica(cliente, upstream):
    r = await cliente.get("/users/user/all")
    assert r.status_code == 401
    assert upstream.request is None


async def test_prefijo_publico_no_matchea_por_substring(cliente, upstream):
    """`auth/login` es público pero `auth/loginX` no debe serlo."""
    r = await cliente.get("/users/auth/loginX")
    assert r.status_code == 401
    assert upstream.request is None
