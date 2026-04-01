from fastapi import FastAPI, Request, HTTPException, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
import json
import httpx
import os

from utils.funtions import get_current_user_smart, is_circuit_open, record_failure, record_success
from utils.redis_client import init_redis, close_redis, get_redis_client

load_dotenv()
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")
USER_ROUTE = os.getenv("USER_ROUTE", "http://app-users:8001")
SANCTIONING_ROUTE = os.getenv("SANCTIONING_ROUTE", "http://app-sanctioning:8002")
DOCUMENTS_ROUTE = os.getenv("DOCUMENTS_ROUTE", "http://app-docs:8003")
INVOLVED_ROUTE = os.getenv("INVOLVED_ROUTE", "http://app-involved:8004")

MICROSERVICES = {
    "users": USER_ROUTE,
    "sanctioning": SANCTIONING_ROUTE,
    "documents": DOCUMENTS_ROUTE,
    "involveds": INVOLVED_ROUTE,
}

PUBLIC_ROUTES = {
    "auth/login",
    "auth/register",
    "auth/recovery-code",
    "auth/recovery",
    "auth/logout",
    "role/permission/verify",
    "user/batch",
    "user/permission",
    "notification/new",
    "notification/add",
    "email/send",
    "email/send-bulk",
    "email/send-alert-report",
    "health"
}

app = FastAPI()

http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(20.0, connect=5.0),
    limits=httpx.Limits(
        max_connections=200,
        max_keepalive_connections=50,
        keepalive_expiry=30.0
    ),
    follow_redirects=True,
    http2=True
)

app.add_middleware(GZipMiddleware, minimum_size=2000, compresslevel=6)

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

EXCLUDED_REQUEST_HEADERS = {
    "host", "content-length", "transfer-encoding", "connection",
    "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "upgrade"
}

EXCLUDED_RESPONSE_HEADERS = {
    "content-encoding", "transfer-encoding", "connection",
    "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "upgrade"
}


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
    token: str = None
):
    if service not in MICROSERVICES:
        raise HTTPException(status_code=404, detail="Service not found")

    if is_circuit_open(service):
        raise HTTPException(status_code=503, detail=f"Service {service} temporarily unavailable")

    is_public = path in PUBLIC_ROUTES or any(path.startswith(pub + "/") for pub in PUBLIC_ROUTES)

    token_data = None
    if not is_public:
        final_token = token if token and "notification/stream" in path else access_token
        token_data = await get_current_user_smart(final_token)

    headers = {"X-Gateway-Token": SECRET_GATEWAY}

    if token_data:
        headers["X-Gateway-User-Id"] = str(token_data["user_id"])
        headers["X-Gateway-Role-Id"] = str(token_data["rol_id"])
        headers["X-Gateway-Name"] = str(token_data["nombre"])
        headers["X-Gateway-Document"] = str(token_data["documento"])
        headers["X-Gateway-Permissions"] = json.dumps(token_data["permisos"])


    for key, value in request.headers.items():
        if key.lower() not in EXCLUDED_REQUEST_HEADERS and value:
            headers[key] = value.strip() if isinstance(value, str) else value

    if "content-type" not in headers and request.method in ("POST", "PUT", "PATCH"):
        headers["content-type"] = "application/json"

    target_url = f"{MICROSERVICES[service]}/{path}"

    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()

    cookies_dict = {}
    if access_token:
        cookies_dict["access_token"] = access_token

    try:
        is_sse = "notification/stream" in path
        is_large_download = "download-all" in path
        timeout_config = httpx.Timeout(300.0, connect=5.0) if (is_sse or is_large_download) else httpx.Timeout(20.0, connect=5.0)

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
        raise HTTPException(status_code=503, detail=f"Service unavailable: {str(e)}")

    response_headers = {
        key: value for key, value in backend_resp.headers.items()
        if key.lower() not in EXCLUDED_RESPONSE_HEADERS and value
    }

    content_type = backend_resp.headers.get("content-type", "")
    content_length = backend_resp.headers.get("content-length")
    is_sse = "text/event-stream" in content_type
    is_large_file = content_length and int(content_length) > 1_000_000

    if is_sse or is_large_file:
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