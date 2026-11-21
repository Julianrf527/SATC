"""FilesClient: contrato de dueños/usos, subida a nombre de usuario,
download_stream con rangos y el helper respuesta_archivo."""
import json

import httpx
import pytest

from satc_shared.archivos import content_disposition, respuesta_archivo
from satc_shared.clients import FilesClient, NotFoundError, ServiceAuthError
from satc_shared.clients.models import UsoArchivo

SECRET = "infra-secret"
DATOS = b"%PDF-1.4 0123456789"


def make(handler):
    return FilesClient("http://docs:1", service_name="infraction-service", secret_key=SECRET,
                       transport=httpx.MockTransport(handler))


# --------------------------------------------------------------- usos

async def test_increment_formato_anterior_y_nuevo():
    cuerpos = []

    def handler(request):
        cuerpos.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "registrados": 1, "no_encontrados": [4]})

    files = make(handler)
    await files.increment_usage([9])
    r = await files.increment_usage(
        usos=[{"file_id": 9, "entidad": "acto", "entidad_id": 55}, UsoArchivo(file_id=4, entidad="oficio", entidad_id="x")],
        usuario_id=7,
    )
    assert cuerpos[0] == {"file_ids": [9]}
    assert cuerpos[1] == {"usos": [{"file_id": 9, "entidad": "acto", "entidad_id": "55"},
                                   {"file_id": 4, "entidad": "oficio", "entidad_id": "x"}], "usuario_id": 7}
    assert r.ok and r.registrados == 1 and r.no_encontrados == [4]


async def test_increment_rechazado_devuelve_ok_false_sin_lanzar():
    def handler(request):
        return httpx.Response(403, json={"ok": False, "message": "ajenos", "rechazados": [3]})

    r = await make(handler).increment_usage(usos=[{"file_id": 3, "entidad": "acto", "entidad_id": 1}], usuario_id=7)
    assert r.ok is False and r.rechazados == [3]


async def test_increment_403_de_autenticacion_lanza():
    def handler(request):
        return httpx.Response(403, json={"detail": "Service token inválido"})

    with pytest.raises(ServiceAuthError):
        await make(handler).increment_usage([3])


async def test_decrement_y_registrar_usos():
    vistos = []

    def handler(request):
        vistos.append((request.method, request.url.path, json.loads(request.content)))
        return httpx.Response(200, json={"ok": True, "quitados": 1, "registrados": 2})

    files = make(handler)
    assert (await files.decrement_usage(usos=[{"file_id": 1, "entidad": "acto", "entidad_id": 2}])).quitados == 1
    assert (await files.registrar_usos([{"file_id": 1, "entidad": "acto", "entidad_id": 2}])).registrados == 2
    assert vistos[0] == ("PUT", "/files/decrement-usage", {"usos": [{"file_id": 1, "entidad": "acto", "entidad_id": "2"}]})
    assert vistos[1] == ("POST", "/files/registrar-usos", {"usos": [{"file_id": 1, "entidad": "acto", "entidad_id": "2"}]})


async def test_upload_a_nombre_de_usuario():
    def handler(request):
        assert b'name="usuario_id"' in request.content and b"\r\n\r\n7\r\n" in request.content
        return httpx.Response(200, json={"ok": True, "file_id": 1, "file_url": "u", "file_hash": "h"})

    assert (await make(handler).upload("a.pdf", b"x", "application/pdf", usuario_id=7)).file_id == 1


# ------------------------------------------------------ download_stream

def _servidor_rangos(request):
    """app-docs falso: 206 con Range, 416 fuera de rango, 404 para el id 404."""
    if request.url.path.endswith("/404"):
        return httpx.Response(404, json={"detail": "Archivo no encontrado"})
    base = {"Accept-Ranges": "bytes", "ETag": '"abc"', "Content-Type": "application/pdf",
            "Content-Disposition": 'inline; filename="ab12.pdf"'}
    rango = request.headers.get("range")
    if rango == "bytes=100-":
        return httpx.Response(416, headers={**base, "Content-Range": f"bytes */{len(DATOS)}"})
    if rango:
        inicio, fin = (int(x) for x in rango.removeprefix("bytes=").split("-"))
        parte = DATOS[inicio:fin + 1]
        return httpx.Response(206, content=parte, headers={
            **base, "Content-Range": f"bytes {inicio}-{fin}/{len(DATOS)}", "Content-Length": str(len(parte))})
    return httpx.Response(200, content=DATOS, headers={**base, "Content-Length": str(len(DATOS))})


async def test_download_stream_reenvia_rango():
    def handler(request):
        assert request.headers["range"] == "bytes=0-3" and request.headers["if-range"] == '"abc"'
        assert "x-service-token" in request.headers
        return _servidor_rangos(request)

    async with make(handler).download_stream(9, range="bytes=0-3", if_range='"abc"') as resp:
        assert resp.status_code == 206
        assert await resp.aread() == DATOS[:4]


async def test_download_stream_404_lanza():
    with pytest.raises(NotFoundError):
        async with make(_servidor_rangos).download_stream(404):
            pass


# ------------------------------------------------------ respuesta_archivo

async def _leer(respuesta) -> bytes:
    return b"".join([bloque async for bloque in respuesta.body_iterator])


async def test_respuesta_archivo_completo_con_nombre_original():
    r = await respuesta_archivo(make(_servidor_rangos), 9, {}, nombre="Resolución 12.pdf")
    assert r.status_code == 200
    assert await _leer(r) == DATOS
    assert r.headers["content-length"] == str(len(DATOS))
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["etag"] == '"abc"'
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["content-type"].startswith("application/pdf")
    assert r.headers["content-disposition"] == (
        "inline; filename=\"Resolucion 12.pdf\"; filename*=UTF-8''Resoluci%C3%B3n%2012.pdf"
    )


async def test_respuesta_archivo_parcial_y_416():
    r = await respuesta_archivo(make(_servidor_rangos), 9, {"range": "bytes=2-5"}, nombre="a.pdf")
    assert r.status_code == 206
    assert await _leer(r) == DATOS[2:6]
    assert r.headers["content-range"] == f"bytes 2-5/{len(DATOS)}"
    r = await respuesta_archivo(make(_servidor_rangos), 9, {"range": "bytes=100-"})
    assert r.status_code == 416
    assert r.headers["content-range"] == f"bytes */{len(DATOS)}"


async def test_respuesta_archivo_404_antes_de_responder():
    with pytest.raises(NotFoundError):
        await respuesta_archivo(make(_servidor_rangos), 404, {})


@pytest.mark.parametrize("nombre,esperado", [
    ("informe.pdf", 'attachment; filename="informe.pdf"'),
    (None, 'attachment; filename="archivo"'),
    ('../../etc/"x".pdf', 'attachment; filename="x.pdf"'),
    ("año.pdf", "attachment; filename=\"ano.pdf\"; filename*=UTF-8''a%C3%B1o.pdf"),
])
def test_content_disposition(nombre, esperado):
    assert content_disposition(nombre) == esperado
