import json

import httpx
import pytest
from jose import jwt

from satc_shared.clients import (
    FilesClient,
    InvolvedClient,
    NotFoundError,
    ServiceAuthError,
    ServiceConfigError,
    ServiceResponseError,
    ServiceTimeoutError,
    ServiceUnavailableError,
    UsersClient,
)
from satc_shared.review_process import FileUsageTracker

SECRET = "infra-secret"


def make(cls, handler, base="http://svc:1"):
    return cls(base, service_name="infraction-service", secret_key=SECRET, transport=httpx.MockTransport(handler))


def caller(request: httpx.Request) -> str:
    return jwt.decode(request.headers["x-service-token"], SECRET, algorithms=["HS256"])["service"]


# ------------------------------------------------------------- UsersClient
async def test_users_verify_permission():
    def handler(request):
        assert request.method == "POST" and request.url.path == "/role/verify"
        assert caller(request) == "infraction-service"
        assert json.loads(request.content) == {"user_id": 5, "permission_name": "file_manage"}
        return httpx.Response(200, json={"tiene_permiso": True})

    assert await make(UsersClient, handler).verify_permission(5, "file_manage") is True


async def test_users_batch_y_por_permiso():
    def handler(request):
        if request.url.path == "/user/batch":
            assert json.loads(request.content) == {"user_ids": [1, 2]}
            return httpx.Response(200, json={"data": [{"id": 1, "nombre": "A", "correo": "a@x", "rol": "z"}]})
        assert request.url.path == "/user/permission/docs_review"
        return httpx.Response(200, json={"data": [{"id": 3, "nombre": "C", "correo": "c@x"}]})

    client = make(UsersClient, handler)
    users = await client.users_batch([1, 2])
    assert users[0].id == 1 and users[0].nombre == "A" and users[0].model_extra["rol"] == "z"
    assert (await client.users_by_permission("docs_review"))[0].id == 3
    assert await client.users_batch([]) == []


async def test_users_notification_y_alertas():
    vistos = []

    def handler(request):
        vistos.append((request.url.path, dict(request.url.params), json.loads(request.content)))
        return httpx.Response(201 if request.url.path == "/notification/add" else 200, json={})

    client = make(UsersClient, handler)
    await client.create_notification(mensaje="m", id_vinculada="7", tipo="documento", usuario_id=3)
    await client.send_alert_report(["a@x"], {"k": 1}, title="T")
    assert vistos[0] == ("/notification/add", {}, {"mensaje": "m", "id_vinculada": "7", "tipo": "documento", "usuario_id": 3})
    assert vistos[1] == ("/email/send-alert-report", {"title": "T"}, {"emails": ["a@x"], "alertas_data": {"k": 1}})


async def test_errores_tipados():
    codes = iter([403, 404, 500])

    def handler(request):
        return httpx.Response(next(codes), text="nope")

    client = make(UsersClient, handler)
    with pytest.raises(ServiceAuthError) as e:
        await client.verify_permission(1, "x")
    assert e.value.status_code == 403 and e.value.body == "nope"
    with pytest.raises(NotFoundError):
        await client.verify_permission(1, "x")
    with pytest.raises(ServiceResponseError):
        await client.verify_permission(1, "x")


async def test_timeout_y_red():
    def timeout(request):
        raise httpx.ReadTimeout("t", request=request)

    def caido(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(ServiceTimeoutError):
        await make(UsersClient, timeout).verify_permission(1, "x")
    with pytest.raises(ServiceUnavailableError):
        await make(UsersClient, caido).verify_permission(1, "x")


async def test_sin_secreto():
    client = UsersClient("http://x", service_name="docs-service", secret_key=None)
    with pytest.raises(ServiceConfigError):
        await client.verify_permission(1, "x")


def test_from_env(monkeypatch):
    monkeypatch.setenv("USER_SERVICE_URL", "http://users:9/")
    monkeypatch.setenv("SERVICE_SECRET_KEY", "k")
    monkeypatch.setenv("INVOLVED_SERVICE_URL", "http://inv:4/involved/")
    assert UsersClient.from_env("docs-service").base_url == "http://users:9"
    assert InvolvedClient.from_env("x").base_url == "http://inv:4/involved"
    monkeypatch.delenv("INVOLVED_SERVICE_URL")
    monkeypatch.setenv("INVOLVED_ROUTE", "http://legacy:4")
    assert InvolvedClient.from_env("x").base_url == "http://legacy:4/involved"


# ------------------------------------------------------------- FilesClient
async def test_files_operaciones():
    def handler(request):
        path = request.url.path
        if path == "/files/upload":
            assert b'name="archivo"' in request.content and b"hola" in request.content
            return httpx.Response(200, json={"ok": True, "file_id": 9, "file_url": "u", "file_hash": "h",
                                             "deduplicated": True, "numero_usos": 2})
        if path == "/files/9":
            return httpx.Response(200, json={"ok": True, "data": {"id": 9, "file_url": "u", "numero_usos": 2}})
        if path == "/files/404":
            return httpx.Response(404, json={"detail": "Archivo no encontrado"})
        if path == "/files/batch":
            return httpx.Response(200, json={"ok": True, "data": [{"id": 9, "file_url": "u"}]})
        if path in ("/files/increment-usage", "/files/decrement-usage"):
            assert request.method == "PUT" and json.loads(request.content) == {"file_ids": [9]}
            return httpx.Response(200, json={"ok": True, "message": "1 archivo"})
        if path == "/files/download-unified":
            assert request.headers.get("cookie") == "s=1"
            return httpx.Response(200, content=b"%PDF")
        if path == "/files/download/9":
            return httpx.Response(200, content=b"abc" * 1000)
        raise AssertionError(path)

    files = make(FilesClient, handler)
    up = await files.upload("a.pdf", b"hola", "application/pdf")
    assert up.file_id == 9 and up.deduplicated
    assert (await files.get(9)).numero_usos == 2
    with pytest.raises(NotFoundError):
        await files.get(404)
    assert [f.id for f in await files.batch([9])] == [9]
    assert await files.batch([]) == []
    assert (await files.increment_usage([9])).ok
    assert (await files.decrement_usage([9])).ok
    assert await files.download_unified([9], cookies={"s": "1"}) == b"%PDF"
    async with files.download(9) as resp:
        data = b"".join([c async for c in resp.aiter_bytes()])
    assert data == b"abc" * 1000
    assert await files.download_bytes(9) == b"abc" * 1000
    assert isinstance(files, FileUsageTracker)


async def test_files_download_error_stream():
    def handler(request):
        return httpx.Response(404, text="no")

    with pytest.raises(NotFoundError):
        async with make(FilesClient, handler).download(1):
            pass


# ---------------------------------------------------------- InvolvedClient
async def test_involved_bulk():
    def handler(request):
        assert request.url.path == "/involved/bulk"
        ids = json.loads(request.content)["ids"]
        if ids == [0]:
            return httpx.Response(200, json={"ok": False})
        return httpx.Response(200, json={"ok": True, "data": [{"id": i, "nombre": "x"} for i in ids]})

    client = make(InvolvedClient, handler, base="http://inv:4")
    assert [d["id"] for d in await client.bulk([1, 2])] == [1, 2]
    assert await client.bulk([]) == []
    with pytest.raises(ServiceResponseError):
        await client.bulk([0])
