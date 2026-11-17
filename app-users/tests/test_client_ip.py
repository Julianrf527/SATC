"""IP real del cliente en el login (límite y bloqueo por IP, no globales).

Tras nginx -> api-gateway, `request.client.host` es siempre el gateway; el
gateway manda la IP real en `X-Gateway-Client-IP` y app-users solo la acepta si
la petición trae un `X-Gateway-Token` válido.
"""
import os
import time

import pytest

import utils.rate_limiter as rl

LOGIN_MINUTO = rl.RateLimiter.LIMITS["login"]["per_minute"]


class RedisSyncFalso:
    """Subconjunto en memoria del cliente redis síncrono que usa rate_limiter."""

    def __init__(self):
        self.valores = {}
        self.expira = {}

    def incr(self, key):
        self.valores[key] = int(self.valores.get(key, 0)) + 1
        return self.valores[key]

    def ttl(self, key):
        if key not in self.valores:
            return -2
        if key not in self.expira:
            return -1
        return max(int(self.expira[key] - time.time()), 0)

    def expire(self, key, segundos):
        self.expira[key] = time.time() + segundos

    def setex(self, key, segundos, valor):
        self.valores[key] = valor
        self.expira[key] = time.time() + segundos

    def get(self, key):
        return self.valores.get(key)

    def delete(self, *keys):
        for k in keys:
            self.valores.pop(k, None)
            self.expira.pop(k, None)


@pytest.fixture
def redis_limiter(monkeypatch):
    falso = RedisSyncFalso()
    monkeypatch.setattr(rl, "redis_client", falso)
    return falso


def _desde_gateway(ip: str) -> dict:
    return {"x-gateway-token": os.environ["SECRET_GATEWAY"], "x-gateway-client-ip": ip}


async def _login_fallido(client, headers, correo):
    return await client.post(
        "/auth/login", json={"email": correo, "password": "mala"}, headers=headers
    )


@pytest.mark.asyncio
async def test_ips_distintas_no_comparten_contador(client, redis_limiter):
    # Se agota el límite por minuto desde una IP (correos distintos para no
    # disparar antes el bloqueo por cuenta)...
    for i in range(LOGIN_MINUTO):
        resp = await _login_fallido(client, _desde_gateway("10.0.0.1"), f"a{i}@test.com")
        assert resp.status_code == 401
    resp = await _login_fallido(client, _desde_gateway("10.0.0.1"), "ultimo@test.com")
    assert resp.status_code == 429

    # ...y otra IP detrás del mismo gateway sigue pudiendo intentar.
    resp = await _login_fallido(client, _desde_gateway("10.0.0.2"), "otro@test.com")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bloqueo_por_cuenta_es_por_ip(client, redis_limiter):
    correo = "victima@test.com"
    for _ in range(5):
        await _login_fallido(client, _desde_gateway("10.0.0.1"), correo)
    resp = await _login_fallido(client, _desde_gateway("10.0.0.1"), correo)
    assert resp.status_code == 429

    resp = await _login_fallido(client, _desde_gateway("10.0.0.2"), correo)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_ip_falsificada_sin_gateway_token_se_ignora(client, redis_limiter):
    # Sin token del gateway la cabecera no vale: todo cuenta contra el par TCP.
    for i in range(LOGIN_MINUTO):
        await _login_fallido(client, {"x-gateway-client-ip": f"10.1.0.{i}"}, f"b{i}@test.com")
    resp = await _login_fallido(client, {"x-gateway-client-ip": "10.1.1.1"}, "c@test.com")
    assert resp.status_code == 429
    assert not any("10.1." in k for k in redis_limiter.valores)


@pytest.mark.asyncio
async def test_ip_falsificada_con_gateway_token_invalido_se_ignora(client, redis_limiter):
    headers = {"x-gateway-token": "robado", "x-gateway-client-ip": "10.9.9.9"}
    await _login_fallido(client, headers, "d@test.com")
    assert not any("10.9.9.9" in k for k in redis_limiter.valores)
    assert any("127.0.0.1" in k for k in redis_limiter.valores)


@pytest.mark.asyncio
async def test_ip_no_valida_del_gateway_cae_al_par_tcp(client, redis_limiter):
    await _login_fallido(client, _desde_gateway("no-es-ip"), "e@test.com")
    assert not any("no-es-ip" in k for k in redis_limiter.valores)
