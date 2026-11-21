"""Descargas de archivos: streaming, Range y cabeceras de respuesta.

Las descargas pasan por `GET /<modulo>/archivos/{file_id}` (el módulo valida
el acceso y transmite los bytes de app-docs). El visor de PDF del front pide
los archivos por rangos, así que el gateway debe reenviar Range/If-Range,
devolver 206/416 tal cual con sus cabeceras y no comprimir ni cargar en
memoria el cuerpo.
"""
import httpx
import pytest

import main


class CuerpoEspia(httpx.AsyncByteStream):
    """Cuerpo del backend que registra si se cerró."""

    def __init__(self, trozos):
        self.trozos = trozos
        self.cerrado = False

    async def __aiter__(self):
        for trozo in self.trozos:
            yield trozo

    async def aclose(self):
        self.cerrado = True


@pytest.fixture
def backend(monkeypatch):
    """Configura la respuesta del backend y captura la petición recibida."""
    estado = {"request": None}

    def configurar(status=200, headers=None, cuerpo=b"", stream=None):
        def handler(request):
            estado["request"] = request
            if stream is not None:
                return httpx.Response(status, headers=headers, stream=stream)
            return httpx.Response(status, headers=headers, content=cuerpo)

        monkeypatch.setattr(
            main, "http_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
        )
        return estado

    return configurar


@pytest.fixture
def respuestas_streaming(monkeypatch):
    """Cuenta los StreamingResponse que construye el gateway."""
    creadas = []

    class StreamingEspia(main.StreamingResponse):
        def __init__(self, *args, **kwargs):
            creadas.append(self)
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(main, "StreamingResponse", StreamingEspia)
    return creadas


# ── Detección de rutas de descarga ──────────────────────────────────────────

@pytest.mark.parametrize(
    "path",
    [
        "archivos/15",
        "acto/3/archivos/15",
        "files/download/15",
        "file/download/15",
        "expediente/9/download-all",
    ],
)
def test_rutas_de_descarga(path):
    assert main.es_descarga(path)


@pytest.mark.parametrize(
    "path",
    [
        "archivos",
        "archivos/abc",
        "archivos/15/metadata",
        "misarchivos/15",
        "manage",
        "recurso/1",
    ],
)
def test_rutas_que_no_son_descarga(path):
    assert not main.es_descarga(path)


# ── Range ───────────────────────────────────────────────────────────────────

async def test_range_e_if_range_se_reenvian_al_backend(cliente_autenticado, backend):
    estado = backend(status=206, cuerpo=b"x")
    await cliente_autenticado.get(
        "/recurso/archivos/15",
        headers={"Range": "bytes=0-99", "If-Range": '"etag-1"'},
    )
    assert estado["request"].headers["range"] == "bytes=0-99"
    assert estado["request"].headers["if-range"] == '"etag-1"'


async def test_206_se_devuelve_con_sus_cabeceras_y_sin_gzip(cliente_autenticado, backend):
    cuerpo = b"%PDF" + b"a" * 5000
    backend(
        status=206,
        headers={
            "Content-Type": "application/pdf",
            "Content-Range": f"bytes 0-{len(cuerpo) - 1}/90000",
            "Accept-Ranges": "bytes",
            "Content-Length": str(len(cuerpo)),
            "Content-Disposition": 'inline; filename="acto.pdf"',
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Cache-Control": "private, no-store",
        },
        cuerpo=cuerpo,
    )
    r = await cliente_autenticado.get(
        "/infraction/archivos/15",
        headers={"Range": f"bytes=0-{len(cuerpo) - 1}", "Accept-Encoding": "gzip"},
    )
    assert r.status_code == 206
    assert r.content == cuerpo
    assert r.headers["content-range"] == f"bytes 0-{len(cuerpo) - 1}/90000"
    assert r.headers["accept-ranges"] == "bytes"
    assert r.headers["content-length"] == str(len(cuerpo))
    assert r.headers["content-disposition"] == 'inline; filename="acto.pdf"'
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "private, no-store"
    assert "content-encoding" not in r.headers


async def test_descarga_completa_tampoco_se_comprime(cliente_autenticado, backend):
    """Sin Range (primera petición de pdf.js) la respuesta debe conservar
    Content-Length y no llevar Content-Encoding, o pdf.js no usará rangos."""
    cuerpo = b"a" * 5000
    backend(
        headers={"Content-Type": "application/pdf", "Accept-Ranges": "bytes"},
        cuerpo=cuerpo,
    )
    r = await cliente_autenticado.get(
        "/recurso/archivos/15", headers={"Accept-Encoding": "gzip"}
    )
    assert r.status_code == 200
    assert "content-encoding" not in r.headers
    assert r.headers["content-length"] == str(len(cuerpo))
    assert r.headers["accept-ranges"] == "bytes"


async def test_416_se_devuelve_tal_cual(cliente_autenticado, backend):
    backend(status=416, headers={"Content-Range": "bytes */90000"})
    r = await cliente_autenticado.get(
        "/recurso/archivos/15", headers={"Range": "bytes=99999-"}
    )
    assert r.status_code == 416
    assert r.headers["content-range"] == "bytes */90000"


async def test_rutas_normales_se_siguen_comprimiendo(cliente_autenticado, backend):
    backend(headers={"Content-Type": "application/json"}, cuerpo=b'{"a":"' + b"x" * 5000 + b'"}')
    r = await cliente_autenticado.get("/recurso/manage", headers={"Accept-Encoding": "gzip"})
    assert r.headers["content-encoding"] == "gzip"


# ── Streaming ───────────────────────────────────────────────────────────────

async def test_descarga_se_transmite_y_cierra_la_respuesta_del_backend(
    cliente_autenticado, backend, respuestas_streaming
):
    cuerpo = CuerpoEspia([b"uno-", b"dos-", b"tres"])
    backend(headers={"Content-Type": "application/pdf"}, stream=cuerpo)
    r = await cliente_autenticado.get("/recurso/archivos/15")
    assert r.content == b"uno-dos-tres"
    assert len(respuestas_streaming) == 1
    assert cuerpo.cerrado, "la respuesta del backend quedó abierta"


async def test_respuesta_grande_no_json_se_transmite(
    cliente_autenticado, backend, respuestas_streaming
):
    backend(
        headers={"Content-Type": "application/zip", "Content-Length": "2000000"},
        cuerpo=b"z" * 2_000_000,
    )
    r = await cliente_autenticado.get("/sanctioning/reporte/exportar")
    assert len(r.content) == 2_000_000
    assert len(respuestas_streaming) == 1


async def test_respuesta_pequena_no_se_transmite_y_se_cierra(
    cliente_autenticado, backend, respuestas_streaming
):
    cuerpo = CuerpoEspia([b'{"ok":', b"true}"])
    backend(headers={"Content-Type": "application/json"}, stream=cuerpo)
    r = await cliente_autenticado.get("/recurso/manage")
    assert r.json() == {"ok": True}
    assert respuestas_streaming == []
    assert cuerpo.cerrado


# ── Timeout ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "path, lectura",
    [
        ("/recurso/archivos/15", 300.0),
        ("/documents/files/download/15", 300.0),
        ("/recurso/manage", 20.0),
    ],
)
async def test_timeout_segun_la_ruta(path, lectura, cliente_autenticado, backend):
    estado = backend(cuerpo=b"x")
    await cliente_autenticado.get(path)
    timeout = estado["request"].extensions["timeout"]
    assert timeout["read"] == lectura
    assert timeout["connect"] == 5.0


# ── Fallos y redirects en descargas ─────────────────────────────────────────

async def test_timeout_en_descarga_da_504(cliente_autenticado, monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)

    monkeypatch.setattr(
        main, "http_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    r = await cliente_autenticado.get("/recurso/archivos/15")
    assert r.status_code == 504


async def test_error_de_red_en_descarga_da_503_y_cuenta_para_el_circuito(
    cliente_autenticado, monkeypatch
):
    from utils import funciones

    def handler(request):
        raise httpx.ConnectError("connection refused a app-recurso:8006", request=request)

    monkeypatch.setattr(
        main, "http_client", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    r = await cliente_autenticado.get("/recurso/archivos/15")
    assert r.status_code == 503
    assert "app-recurso" not in r.text
    assert funciones.CIRCUIT_BREAKER["recurso"][0] == 1


async def test_redirect_en_descarga_se_sanea(cliente_autenticado, backend):
    backend(status=302, headers={"Location": "http://app-docs:8003/files/download/15"})
    r = await cliente_autenticado.get("/recurso/archivos/15")
    assert r.status_code == 302
    assert r.headers["location"] == "/documents/files/download/15"
