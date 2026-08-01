from fastapi import FastAPI, Request, HTTPException, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from starlette.background import BackgroundTask
from dotenv import load_dotenv
import logging
import httpx
import os

from utils.funciones import decode_jwt_token, is_circuit_open, record_failure, record_success
from utils.redis_client import init_redis, close_redis, get_redis_client
from utils import rate_limit

logger = logging.getLogger(__name__)

load_dotenv()
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")
USER_ROUTE = os.getenv("USER_ROUTE", "http://app-users:8001")
SANCTIONING_ROUTE = os.getenv("SANCTIONING_ROUTE", "http://app-sanctioning:8002")
DOCUMENTS_ROUTE = os.getenv("DOCUMENTS_ROUTE", "http://app-docs:8003")
INVOLVED_ROUTE = os.getenv("INVOLVED_ROUTE", "http://app-involved:8004")
INFRACTION_ROUTE = os.getenv("INFRACTION_ROUTE", "http://app-infraction:8005")

MICROSERVICES = {
    "users": USER_ROUTE,
    "sanctioning": SANCTIONING_ROUTE,
    "documents": DOCUMENTS_ROUTE,
    "involveds": INVOLVED_ROUTE,
    "infraction": INFRACTION_ROUTE,
}

# Rutas que no exigen sesión de usuario, indexadas POR SERVICIO: un set global
# haría pública cada entrada en los cinco servicios a la vez, y bastaría con que
# un servicio estrenara un endpoint homónimo de una ruta pública de otro para
# convertirlo en un bypass de sesión. Scopear elimina esa clase de bug.
#
# El path es lo que va DESPUÉS del `/{service}/` de la URL:
# /documents/files/increment-usage → service=documents, path=files/increment-usage
PUBLIC_ROUTES = {
    "users": {
        "auth/login",
        "auth/recovery-code",
        "auth/recovery",
        "auth/logout",
        "role/verify",
        "user/batch",
        "user/permission",
        "notification/add",
        "email/send",
        "email/send-bulk",
        "email/send-alert-report",
    },
    # Rutas internas microservicio→docs (sin JWT de usuario; el destino exige
    # X-Service-Token).
    "documents": {
        "files/increment-usage",
        "files/decrement-usage",
        "files/batch",
    },
    "sanctioning": set(),
    "involveds": set(),
    "infraction": set(),
}

# Transversales: los cinco microservicios exponen su propio `/health` y todos
# deben ser alcanzables sin sesión para los healthchecks.
PUBLIC_ROUTES_COMUNES = {
    "health",
}


def es_ruta_publica(service: str, path: str) -> bool:
    """¿`path` es público PARA ESTE servicio en concreto?

    Se acepta el match exacto y el de prefijo de segmento (`user/permission`
    cubre `user/permission/ver_expedientes`), pero nunca el de substring:
    `auth/loginX` no es `auth/login`.
    """
    rutas = PUBLIC_ROUTES.get(service, set()) | PUBLIC_ROUTES_COMUNES
    return path in rutas or any(path.startswith(pub + "/") for pub in rutas)

app = FastAPI()

# follow_redirects se deja en False (default de httpx): el gateway pone
# `X-Gateway-Token: SECRET_GATEWAY` en cada petición al backend, y siguiendo
# redirects un microservicio comprometido podría hacer que el gateway repita la
# petición —con ese token puesto— contra el destino que él elija, filtrando el
# secreto que lo autentica ante todos los servicios. Ningún backend devuelve
# 3xx en rutas proxeadas ni declara rutas con barra final (que dispararían el
# redirect automático de Starlette), así que no afecta ningún flujo real.
http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(20.0, connect=5.0),
    limits=httpx.Limits(
        max_connections=200,
        max_keepalive_connections=50,
        keepalive_expiry=30.0
    ),
    http2=True
)


class RateLimitMiddleware:
    """Límite por IP sobre toda la superficie pública del gateway.

    Va en middleware y no dentro de `proxy` para contar también lo que nunca
    llega al handler (servicios inexistentes, paths con traversal): si no, un
    atacante podría inundar el gateway con 404s sin gastar cuota.

    Es ASGI puro y no `BaseHTTPMiddleware` a propósito: el proxy devuelve
    `StreamingResponse` para SSE y descargas grandes, y BaseHTTPMiddleware
    encola el cuerpo internamente, lo que añade latencia al streaming y
    complica el ciclo de vida del `BackgroundTask` que cierra el cliente SSE.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # `/health` se exime: el healthcheck del contenedor y el de nginx pegan
        # cada 10-30s y un pico de tráfico no debe poder tumbarlo y provocar un
        # reinicio en bucle. Es un endpoint sin datos ni coste.
        request = Request(scope)
        if request.url.path == "/health":
            return await self.app(scope, receive, send)

        ip = rate_limit.obtener_ip_cliente(request)
        # `/{service}/{path}` → path relativo al servicio, que es sobre el que
        # están definidos los prefijos de auth.
        partes = request.url.path.lstrip("/").split("/", 1)
        path_servicio = partes[1] if len(partes) > 1 else ""

        espera = await rate_limit.verificar_ip(get_redis_client(), ip, path_servicio)
        if espera is not None:
            logger.warning(f"Rate limit por IP excedido: {ip} -> {request.url.path}")
            respuesta = JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(espera)},
            )
            return await respuesta(scope, receive, send)

        return await self.app(scope, receive, send)


app.add_middleware(GZipMiddleware, minimum_size=2000, compresslevel=6)

# `add_middleware` antepone, así que el último agregado es el más externo: la
# pila queda CORS → RateLimit → GZip → app. CORS debe ir por fuera para que el
# 429 lleve cabeceras CORS (si no el navegador ve un error opaco) y para que el
# preflight OPTIONS se responda sin gastar cuota.
app.add_middleware(RateLimitMiddleware)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# Cabeceras de confianza que el gateway inyecta él mismo. Se descartan SIEMPRE
# de la petición entrante: los microservicios confían ciegamente en ellas para
# identificar al usuario, así que reenviar la versión del cliente equivale a
# permitir suplantación total. Ningún servicio interno llama a través del
# gateway (todos usan la URL directa app-*:800x), así que descartarlas no rompe
# ningún flujo service-to-service.
TRUST_HEADERS = {
    "x-gateway-token", "x-gateway-user-id", "x-gateway-role-id", "x-service-token",
}

EXCLUDED_REQUEST_HEADERS = {
    "host", "content-length", "transfer-encoding", "connection",
    "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "upgrade", "cookie",
} | TRUST_HEADERS

EXCLUDED_RESPONSE_HEADERS = {
    "content-encoding", "transfer-encoding", "connection",
    "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "upgrade"
}


def tiene_traversal(path: str) -> bool:
    """Detecta segmentos `.`/`..` en el path.

    La pertenencia a PUBLIC_ROUTES se evalúa sobre el path tal como llega, pero
    httpx colapsa los segmentos punto al construir la URL destino. Sin este
    chequeo, `health/../user/all` matchea el prefijo público `health/` y termina
    llegando a `/user/all` sin validación de sesión.
    """
    return any(seg in (".", "..") for seg in path.split("/"))


def sanear_redireccion(service: str, status_code: int, headers: dict) -> None:
    """Reescribe el `Location` de una respuesta 3xx del backend, in-place.

    Como el gateway no sigue redirects, el 3xx llega tal cual al navegador y su
    `Location` apuntaría a un host de la red privada (`http://app-users:8001`),
    que el cliente no puede resolver y que revela la topología interna; se
    traduce a la ruta equivalente del gateway.

    Si apunta a un host desconocido se elimina la cabecera y se registra: que un
    servicio interno intente mandar al cliente afuera es anómalo.
    """
    if not (300 <= status_code < 400):
        return

    clave = next((k for k in headers if k.lower() == "location"), None)
    if clave is None:
        return

    destino = headers[clave]

    if destino.startswith("/"):
        headers[clave] = f"/{service}{destino}"
        return

    for nombre, base in MICROSERVICES.items():
        if destino.startswith(base + "/") or destino == base:
            headers[clave] = f"/{nombre}{destino[len(base):]}"
            return

    logger.warning(
        f"El servicio {service} devolvió un redirect a un destino externo; "
        f"se descarta la cabecera Location"
    )
    del headers[clave]


@app.on_event("startup")
async def startup_event():
    await init_redis()


@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()
    await close_redis()


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(
    service: str,
    path: str,
    request: Request,
    access_token: str = Cookie(None),
):
    if service not in MICROSERVICES:
        raise HTTPException(status_code=404, detail="Service not found")

    if tiene_traversal(path):
        raise HTTPException(status_code=400, detail="Invalid path")

    if is_circuit_open(service):
        raise HTTPException(status_code=503, detail=f"Service {service} temporarily unavailable")

    is_public = es_ruta_publica(service, path)

    token_data = None

    if not is_public:
        token_data = decode_jwt_token(access_token)

        r = get_redis_client()

        if not r:
            raise HTTPException(503, "No se pudo validar sesión")

        # Fail-closed: si la sesión no existe en Redis el token no vale. El
        # logout borra esta clave, así que tolerar su ausencia haría que una
        # cookie ya deslogueada siguiera siendo válida hasta su exp.
        stored_jti = await r.get(f"session:user:{token_data['user_id']}")
        if not stored_jti:
            raise HTTPException(401, detail="session_expired")
        if stored_jti != token_data["jti"]:
            raise HTTPException(401, detail="session_replaced")

        # Límite por usuario, además del de IP que ya aplicó el middleware: con
        # media oficina saliendo por la misma IP pública, un solo usuario podría
        # consumir la cuota de todos sus compañeros.
        espera = await rate_limit.verificar_usuario(r, token_data["user_id"])
        if espera is not None:
            logger.warning(f"Rate limit por usuario excedido: {token_data['user_id']}")
            raise HTTPException(
                status_code=429,
                detail="Too many requests",
                headers={"Retry-After": str(espera)},
            )

    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in EXCLUDED_REQUEST_HEADERS and value:
            headers[key] = value.strip() if isinstance(value, str) else value

    # Se inyectan después del copiado para que ninguna cabecera del cliente
    # pueda ganarle a las de confianza.
    headers["X-Gateway-Token"] = SECRET_GATEWAY

    if token_data:
        headers["X-Gateway-User-Id"] = str(token_data["user_id"])
        headers["X-Gateway-Role-Id"] = str(token_data["rol_id"])

    if "content-type" not in headers and request.method in ("POST", "PUT", "PATCH"):
        headers["content-type"] = "application/json"

    target_url = f"{MICROSERVICES[service]}/{path}"

    body = None
    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        body = await request.body()

    cookies_dict = {}
    if access_token:
        cookies_dict["access_token"] = access_token

    is_sse = "notification/stream" in path
    is_large_download = "download-all" in path or "file/download/" in path

    if is_sse:
        # Sin follow_redirects, por el mismo motivo que `http_client`: no
        # arrastrar X-Gateway-Token a un destino que elija el backend.
        sse_client = httpx.AsyncClient(
            timeout=httpx.Timeout(None, connect=5.0),
            http2=True,
        )
        req = sse_client.build_request(
            request.method,
            target_url,
            headers=headers,
            params=request.query_params,
            content=body,
            cookies=cookies_dict,
        )
        try:
            backend_resp = await sse_client.send(
                req,
                stream=True,
            )
            record_success(service)
        except httpx.TimeoutException:
            await sse_client.aclose()
            record_failure(service)
            raise HTTPException(status_code=504, detail="Gateway timeout")
        except httpx.RequestError as e:
            await sse_client.aclose()
            record_failure(service)
            logger.warning(f"Fallo de red hacia {service}: {e}")
            raise HTTPException(status_code=503, detail="Service unavailable")

        async def close_sse_resources():
            await backend_resp.aclose()
            await sse_client.aclose()

        response_headers = {
            key: value for key, value in backend_resp.headers.items()
            if key.lower() not in EXCLUDED_RESPONSE_HEADERS and value
        }
        sanear_redireccion(service, backend_resp.status_code, response_headers)
        content_type = backend_resp.headers.get("content-type", "text/event-stream")

        return StreamingResponse(
            backend_resp.aiter_bytes(),
            status_code=backend_resp.status_code,
            headers=response_headers,
            media_type=content_type,
            background=BackgroundTask(close_sse_resources),
        )

    try:
        timeout_config = httpx.Timeout(300.0, connect=5.0) if is_large_download else httpx.Timeout(20.0, connect=5.0)

        backend_resp = await http_client.request(
            request.method,
            target_url,
            headers=headers,
            params=request.query_params,
            content=body,
            cookies=cookies_dict,
            timeout=timeout_config,
        )
        record_success(service)
    except httpx.TimeoutException:
        record_failure(service)
        raise HTTPException(status_code=504, detail="Gateway timeout")
    except httpx.RequestError as e:
        record_failure(service)
        logger.warning(f"Fallo de red hacia {service}: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

    response_headers = {
        key: value for key, value in backend_resp.headers.items()
        if key.lower() not in EXCLUDED_RESPONSE_HEADERS and value
    }
    sanear_redireccion(service, backend_resp.status_code, response_headers)

    content_type = backend_resp.headers.get("content-type", "")
    content_length = backend_resp.headers.get("content-length")
    respuesta_es_sse = "text/event-stream" in content_type
    is_large_file = bool(content_length and content_length.isdigit() and int(content_length) > 1_000_000)

    if respuesta_es_sse or is_large_file:
        return StreamingResponse(
            backend_resp.aiter_bytes(),
            status_code=backend_resp.status_code,
            headers=response_headers,
            media_type=content_type
        )

    return Response(
        content=backend_resp.content,
        status_code=backend_resp.status_code,
        headers=response_headers,
        media_type=backend_resp.headers.get("content-type")
    )


@app.get("/health")
async def health_check():
    r = get_redis_client()
    redis_status = "healthy" if r is not None else "unavailable"

    return {
        "status": "healthy",
        "services": list(MICROSERVICES.keys()),
        "redis": redis_status
    }