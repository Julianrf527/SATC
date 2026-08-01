"""Cabeceras de confianza: el gateway es la única fuente de identidad.

Los microservicios confían ciegamente en `X-Gateway-User-Id`/`X-Gateway-Role-Id`
(ver `utils/verify_token.py` de cada servicio) y en `X-Service-Token` para las
llamadas internas. Si el gateway reenviara la versión que mandó el cliente,
cualquiera podría suplantar a un usuario o a un microservicio.
"""
import pytest

import main

CABECERAS_FORJADAS = {
    "X-Gateway-Token": "robado",
    "X-Gateway-User-Id": "99",
    "X-Gateway-Role-Id": "99",
    "X-Service-Token": "forjado",
}


async def test_cliente_no_puede_suplantar_usuario_en_ruta_protegida(
    cliente_autenticado, upstream
):
    await cliente_autenticado.get("/users/user/all", headers=CABECERAS_FORJADAS)
    assert upstream.headers["X-Gateway-User-Id"] == "1"
    assert upstream.headers["X-Gateway-Role-Id"] == "1"
    assert upstream.headers["X-Gateway-Token"] == main.SECRET_GATEWAY
    assert "x-service-token" not in upstream.headers


async def test_cliente_no_puede_inyectar_identidad_en_ruta_publica(cliente, upstream):
    """El caso peligroso: en rutas públicas el gateway no declara usuario, así
    que una cabecera del cliente que sobreviva llegaría sin ninguna otra
    validación al microservicio."""
    await cliente.post("/users/user/batch", json={}, headers=CABECERAS_FORJADAS)
    assert "x-gateway-user-id" not in upstream.headers
    assert "x-gateway-role-id" not in upstream.headers
    assert "x-service-token" not in upstream.headers
    assert upstream.headers["X-Gateway-Token"] == main.SECRET_GATEWAY


@pytest.mark.parametrize("cabecera", sorted(main.TRUST_HEADERS))
async def test_toda_cabecera_de_confianza_se_descarta(cabecera, cliente, upstream):
    await cliente.get("/users/health", headers={cabecera: "valor-del-cliente"})
    assert upstream.headers.get(cabecera) != "valor-del-cliente"


async def test_gateway_token_siempre_presente(cliente, upstream):
    await cliente.get("/users/health")
    assert upstream.headers["X-Gateway-Token"] == main.SECRET_GATEWAY


async def test_cabeceras_hop_by_hop_no_se_reenvian(cliente_autenticado, upstream):
    await cliente_autenticado.get(
        "/users/recurso", headers={"Connection": "keep-alive", "TE": "trailers"}
    )
    assert "te" not in upstream.headers


async def test_cookie_cruda_no_se_reenvia_entera(cliente_autenticado, upstream):
    """Solo `access_token` viaja al backend; el resto de cookies del navegador
    (analytics, sesiones de terceros) no debe filtrarse a la red interna."""
    cliente_autenticado.cookies.set("cookie_ajena", "secreto")
    await cliente_autenticado.get("/users/recurso")
    assert "secreto" not in upstream.headers.get("cookie", "")
    assert "access_token=" in upstream.headers.get("cookie", "")


async def test_cabeceras_normales_del_cliente_se_reenvian(cliente_autenticado, upstream):
    await cliente_autenticado.get("/users/recurso", headers={"Accept-Language": "es-CO"})
    assert upstream.headers["accept-language"] == "es-CO"
