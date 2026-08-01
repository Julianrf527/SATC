"""Rate limiting en el gateway.

El gateway es el único punto de entrada público, así que es el sitio correcto
para el primer filtro de abuso: hasta ahora lo único que existía era el throttle
por cuenta de `app-users` en `auth/login`, que no ve el password-spraying (una
contraseña contra muchas cuentas) ni protege al resto de la superficie.
"""
import pytest

import main
from utils import rate_limit
from conftest import RedisFalso, crear_token


@pytest.fixture(autouse=True)
def limites_por_defecto(monkeypatch):
    """Fija límites conocidos para no depender del entorno."""
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(rate_limit, "LIMITE_IP_MAX", 5)
    monkeypatch.setattr(rate_limit, "LIMITE_IP_VENTANA", 60)
    monkeypatch.setattr(rate_limit, "LIMITE_AUTH_MAX", 2)
    monkeypatch.setattr(rate_limit, "LIMITE_AUTH_VENTANA", 300)
    monkeypatch.setattr(rate_limit, "LIMITE_USUARIO_MAX", 3)
    monkeypatch.setattr(rate_limit, "LIMITE_USUARIO_VENTANA", 60)


# ── Límite general por IP ───────────────────────────────────────────────────

async def test_bajo_el_limite_pasa(cliente, upstream):
    for _ in range(rate_limit.LIMITE_IP_MAX):
        r = await cliente.get("/users/health")
        assert r.status_code == 200


async def test_al_exceder_el_limite_da_429(cliente, upstream):
    for _ in range(rate_limit.LIMITE_IP_MAX):
        await cliente.get("/users/health")

    r = await cliente.get("/users/health")
    assert r.status_code == 429
    assert r.json()["detail"] == "Too many requests"


async def test_429_incluye_retry_after_util(cliente, upstream):
    for _ in range(rate_limit.LIMITE_IP_MAX + 1):
        r = await cliente.get("/users/health")

    assert r.status_code == 429
    retry = r.headers["Retry-After"]
    assert retry.isdigit()
    assert 0 < int(retry) <= rate_limit.LIMITE_IP_VENTANA


async def test_429_no_llega_al_microservicio(cliente, upstream, monkeypatch):
    for _ in range(rate_limit.LIMITE_IP_MAX):
        await cliente.get("/users/health")

    upstream.request = None
    r = await cliente.get("/users/health")
    assert r.status_code == 429
    assert upstream.request is None, "el gateway proxeó una petición ya limitada"


async def test_el_limite_cuenta_tambien_lo_que_no_llega_al_handler(cliente, upstream):
    """404s y paths inválidos también gastan cuota: si no, se podría inundar
    el gateway con peticiones a servicios inexistentes sin coste."""
    for _ in range(rate_limit.LIMITE_IP_MAX):
        r = await cliente.get("/servicio-inexistente/algo")
        assert r.status_code == 404

    r = await cliente.get("/servicio-inexistente/algo")
    assert r.status_code == 429


async def test_health_del_gateway_esta_exento(cliente):
    """El healthcheck del contenedor pega acá; limitarlo lo reiniciaría en bucle."""
    for _ in range(rate_limit.LIMITE_IP_MAX * 3):
        r = await cliente.get("/health")
        assert r.status_code == 200


# ── Identidad del cliente ───────────────────────────────────────────────────

async def test_ips_distintas_tienen_cuotas_independientes(cliente, upstream):
    for _ in range(rate_limit.LIMITE_IP_MAX + 1):
        r = await cliente.get("/users/health", headers={"X-Real-IP": "10.0.0.1"})
    assert r.status_code == 429

    r = await cliente.get("/users/health", headers={"X-Real-IP": "10.0.0.2"})
    assert r.status_code == 200


async def test_x_forwarded_for_se_lee_por_la_derecha(cliente, upstream):
    """nginx *anexa* la IP real al final de lo que mandó el cliente
    (`$proxy_add_x_forwarded_for`), así que el último elemento es el único no
    falsificable. Leyendo el primero, cualquiera evadiría el límite rotando la
    IP que declara."""
    for i in range(rate_limit.LIMITE_IP_MAX + 1):
        r = await cliente.get(
            "/users/health",
            headers={"X-Forwarded-For": f"1.2.3.{i}, 203.0.113.9"},
        )

    assert r.status_code == 429, (
        "el atacante evadió el límite falsificando el primer elemento de XFF"
    )


def test_obtener_ip_prioriza_x_real_ip():
    class ReqFalsa:
        headers = {"x-real-ip": "10.0.0.5", "x-forwarded-for": "1.1.1.1, 10.0.0.9"}
        client = type("C", (), {"host": "172.20.0.3"})()

    assert rate_limit.obtener_ip_cliente(ReqFalsa()) == "10.0.0.5"


def test_obtener_ip_cae_a_la_conexion_sin_cabeceras():
    class ReqFalsa:
        headers = {}
        client = type("C", (), {"host": "172.20.0.3"})()

    assert rate_limit.obtener_ip_cliente(ReqFalsa()) == "172.20.0.3"


# ── Límite estricto de autenticación ────────────────────────────────────────

@pytest.mark.parametrize(
    "ruta", ["auth/login", "auth/recovery", "auth/recovery-code"]
)
def test_rutas_de_auth_reconocidas(ruta):
    assert rate_limit.es_ruta_auth(ruta)


@pytest.mark.parametrize("ruta", ["user/all", "health", "authenticate", "auth"])
def test_rutas_normales_no_son_de_auth(ruta):
    assert not rate_limit.es_ruta_auth(ruta)


async def test_login_corta_antes_que_el_limite_general(cliente, upstream):
    """Defensa en profundidad: el límite de auth (2) es más estricto que el
    general (5), así que la fuerza bruta se frena mucho antes."""
    for _ in range(rate_limit.LIMITE_AUTH_MAX):
        r = await cliente.post("/users/auth/login", json={"a": 1})
        assert r.status_code == 200

    r = await cliente.post("/users/auth/login", json={"a": 1})
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) <= rate_limit.LIMITE_AUTH_VENTANA


async def test_el_limite_de_auth_no_afecta_a_rutas_normales(cliente, upstream):
    for _ in range(rate_limit.LIMITE_AUTH_MAX + 1):
        await cliente.post("/users/auth/login", json={"a": 1})

    # Aún queda cuota general: el flood de login no debe dejar sin servicio al
    # resto de la API para esa IP más allá de lo que gastó.
    r = await cliente.get("/users/health")
    assert r.status_code == 200


async def test_recovery_tambien_esta_limitado(cliente, upstream):
    for _ in range(rate_limit.LIMITE_AUTH_MAX):
        await cliente.post("/users/auth/recovery-code", json={})

    r = await cliente.post("/users/auth/recovery-code", json={})
    assert r.status_code == 429


# ── Límite por usuario autenticado ──────────────────────────────────────────

async def test_usuario_autenticado_tiene_su_propia_cuota(cliente, redis_con, upstream):
    """Detrás de una NAT compartida el límite por IP no distingue usuarios; este
    evita que uno solo consuma la cuota de toda la oficina."""
    token, jti = crear_token()
    redis_con({"session:user:1": jti})
    cliente.cookies.set("access_token", token)

    for _ in range(rate_limit.LIMITE_USUARIO_MAX):
        r = await cliente.get("/users/user/all")
        assert r.status_code == 200

    r = await cliente.get("/users/user/all")
    assert r.status_code == 429
    assert r.headers["Retry-After"].isdigit()
    cliente.cookies.clear()


async def test_limite_de_usuario_se_aplica_tras_validar_sesion(
    cliente, redis_con, upstream
):
    """Un token inválido debe seguir dando 401, no 429: el orden importa para
    no filtrar si una sesión existe o no."""
    redis_con({"session:user:1": "otro-jti"})
    token, _ = crear_token()
    cliente.cookies.set("access_token", token)

    for _ in range(rate_limit.LIMITE_USUARIO_MAX + 2):
        r = await cliente.get("/users/user/all")
        assert r.status_code == 401
    cliente.cookies.clear()


# ── Modo de fallo ───────────────────────────────────────────────────────────

async def test_sin_redis_las_rutas_publicas_siguen_pasando(cliente, monkeypatch, upstream):
    """Fail-open deliberado: el control de autorización ya falla cerrado por su
    cuenta (sesión → 503), y fallar cerrado acá convertiría un parpadeo de Redis
    en una caída total, healthcheck incluido."""
    monkeypatch.setattr(main, "get_redis_client", lambda: None)

    for _ in range(rate_limit.LIMITE_IP_MAX * 2):
        r = await cliente.get("/users/health")
        assert r.status_code == 200


async def test_redis_que_lanza_excepcion_no_tumba_la_peticion(cliente, monkeypatch, upstream):
    class RedisRoto(RedisFalso):
        def pipeline(self):
            raise RuntimeError("connection reset")

    monkeypatch.setattr(main, "get_redis_client", lambda: RedisRoto())
    r = await cliente.get("/users/health")
    assert r.status_code == 200


async def test_desactivar_por_configuracion(cliente, monkeypatch, upstream):
    monkeypatch.setattr(rate_limit, "RATE_LIMIT_ENABLED", False)

    for _ in range(rate_limit.LIMITE_IP_MAX * 2):
        r = await cliente.get("/users/health")
        assert r.status_code == 200


# ── Ventana ─────────────────────────────────────────────────────────────────

async def test_el_ttl_se_fija_una_sola_vez(upstream):
    """Reiniciar el TTL en cada petición convertiría la ventana fija en un
    baneo deslizante que solo se libera tras silencio total."""
    fake = RedisFalso()
    await rate_limit.consumir(fake, "ratelimit:ip:x", 10, 60)
    fake.ttls["ratelimit:ip:x"] = 42  # simula el paso del tiempo
    await rate_limit.consumir(fake, "ratelimit:ip:x", 10, 60)
    assert fake.ttls["ratelimit:ip:x"] == 42


async def test_consumir_devuelve_none_mientras_haya_cuota():
    fake = RedisFalso()
    for _ in range(3):
        assert await rate_limit.consumir(fake, "k", 3, 60) is None
    assert await rate_limit.consumir(fake, "k", 3, 60) is not None
