"""Autenticación y autorización: ningún endpoint debe responder sin credenciales válidas."""
import pytest

from tests.conftest import gateway_headers, service_headers

pytestmark = pytest.mark.asyncio


RUTAS_GATEWAY = [
    ("get", "/involved/search/CC/1234567890"),
    ("get", "/involved/manage"),
    ("get", "/involved/log"),
    ("get", "/involved/1"),
]


@pytest.mark.parametrize("metodo,ruta", RUTAS_GATEWAY)
async def test_sin_gateway_token_403(client, metodo, ruta):
    r = await getattr(client, metodo)(ruta)
    assert r.status_code == 403


@pytest.mark.parametrize("metodo,ruta", RUTAS_GATEWAY)
async def test_gateway_token_incorrecto_403(client, metodo, ruta):
    r = await getattr(client, metodo)(ruta, headers={"x-gateway-token": "invalido"})
    assert r.status_code == 403


async def test_post_new_sin_gateway_token_403(client):
    r = await client.post("/involved/new", json={
        "numero_documento": 1234567890, "tipo_documento": "CC", "nombre": "X",
    })
    assert r.status_code == 403


async def test_put_sin_gateway_token_403(client):
    r = await client.put("/involved/1", json={"nombre": "X"})
    assert r.status_code == 403


async def test_gateway_sin_user_id_403(client):
    headers = gateway_headers()
    del headers["X-Gateway-User-Id"]
    r = await client.get("/involved/manage", headers=headers)
    assert r.status_code == 403


async def test_gateway_sin_rol_id_403(client):
    headers = gateway_headers()
    del headers["X-Gateway-Role-Id"]
    r = await client.get("/involved/manage", headers=headers)
    assert r.status_code == 403


async def test_gateway_user_id_no_numerico_da_403_no_500(client):
    """Un header de identidad corrupto es un 403, no un ValueError -> 500."""
    headers = gateway_headers()
    headers["X-Gateway-User-Id"] = "no-soy-un-numero"
    r = await client.get("/involved/manage", headers=headers)
    assert r.status_code == 403


async def test_bulk_sin_service_token_403(client):
    r = await client.post("/involved/bulk", json={"ids": [1]})
    assert r.status_code == 403


async def test_bulk_no_acepta_gateway_token(client):
    """/bulk es service-to-service: el gateway token no debe alcanzar."""
    r = await client.post("/involved/bulk", json={"ids": [1]}, headers=gateway_headers())
    assert r.status_code == 403


async def test_bulk_service_token_invalido_403(client):
    r = await client.post(
        "/involved/bulk", json={"ids": [1]}, headers={"x-service-token": "no.es.un.jwt"}
    )
    assert r.status_code == 403


async def test_bulk_con_service_token_valido_200(client):
    r = await client.post("/involved/bulk", json={"ids": [1]}, headers=service_headers())
    assert r.status_code == 200


async def test_health_es_publico(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["service"] == "app-involved"
