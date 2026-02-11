from fastapi import FastAPI, Request, HTTPException, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from datetime import datetime, timedelta
from jose import jwt, JWTError
import httpx
import os
import time
import json

from utils.funtions import get_current_user_smart, invalidate_token_cache, is_circuit_open, record_failure, record_success

load_dotenv()
SECRET_GATEWAY = os.getenv("SECRET_GATEWAY")
SECRET_KEY_GATEWAY = os.getenv("SECRET_KEY_GATEWAY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")
USER_ROUTE = os.getenv("USER_ROUTE")
SANCTIONING_ROUTE = os.getenv("SANCTIONING_ROUTE")
DOCUMENTS_ROUTE = os.getenv("DOCUMENTS_ROUTE")


MICROSERVICES = {
    "users": USER_ROUTE,
    "sanctioning": SANCTIONING_ROUTE,
    "documents": DOCUMENTS_ROUTE,
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
    "email/send-alert-report"
}

app = FastAPI()

http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(20.0, connect=5.0),
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20,
        keepalive_expiry=30.0
    ),
    follow_redirects=True,
    http2=True
)

app.add_middleware(GZipMiddleware, minimum_size=2000, compresslevel=6)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

EXCLUDED_REQUEST_HEADERS = {
    "host",
    "content-length",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "upgrade"
}

EXCLUDED_RESPONSE_HEADERS = {
    "content-encoding",
    "transfer-encoding",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "upgrade"
}



@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(
    service: str, 
    path: str, 
    request: Request, 
    access_token: str = Cookie(None),
    token: str = None  # Query parameter para SSE
):
    if service not in MICROSERVICES:
        raise HTTPException(status_code=404, detail="Service not found")

    if is_circuit_open(service):
        raise HTTPException(
            status_code=503, 
            detail=f"Service {service} is temporarily unavailable"
        )

    is_public = path in PUBLIC_ROUTES or any(path.startswith(pub + "/") for pub in PUBLIC_ROUTES)

    token_data = None
    if not is_public:
        # Para SSE, permitir token via query parameter (EventSource no puede enviar headers)
        final_token = token if token and "notification/stream" in path else access_token
        token_data = get_current_user_smart(final_token, path)

    headers = {
        "X-Gateway-Token": SECRET_GATEWAY,
    }
    
    if token_data:
        headers["X-Gateway-User-Id"] = str(token_data["user_id"])
        # Enviar permisos como JSON string
        headers["X-Gateway-Permissions"] = json.dumps(token_data["permissions"])

    for key, value in request.headers.items():
        if key.lower() not in EXCLUDED_REQUEST_HEADERS and value:
            headers[key] = value.strip() if isinstance(value, str) else value

    if "content-type" not in headers and request.method in ("POST", "PUT", "PATCH"):
        headers["content-type"] = "application/json"

    target_url = f"{MICROSERVICES[service]}/{path}"

    body = None
    if request.method in ("POST", "PUT", "PATCH"):
        body = await request.body()

    try:
        # Para SSE, usar timeout más largo y no esperar la respuesta completa
        timeout_config = httpx.Timeout(300.0, connect=5.0) if "notification/stream" in path else httpx.Timeout(20.0, connect=5.0)
        
        backend_resp = await http_client.request(
            request.method,
            target_url,
            headers=headers,
            params=request.query_params,
            content=body,
            timeout=timeout_config,
        )
        record_success(service)
    except httpx.TimeoutException:
        record_failure(service)
        raise HTTPException(status_code=504, detail="Gateway timeout")
    except httpx.RequestError as e:
        record_failure(service)
        print(f"Error al conectar con microservicio: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"Service unavailable: {str(e)}"
        )

    response_headers = {}
    
    for key, value in backend_resp.headers.items():
        if key.lower() not in EXCLUDED_RESPONSE_HEADERS and value:
            response_headers[key] = value

    # Detectar SSE (Server-Sent Events) o archivos grandes y usar streaming
    content_type = backend_resp.headers.get("content-type", "")
    content_length = backend_resp.headers.get("content-length")
    
    is_sse = "text/event-stream" in content_type
    is_large_file = content_length and int(content_length) > 1_000_000
    
    if is_sse or is_large_file:
        return StreamingResponse(
            backend_resp.aiter_bytes(),
            status_code=backend_resp.status_code,
            headers=response_headers,
            media_type=content_type or backend_resp.headers.get("content-type")
        )

    if path == "auth/logout":
        invalidate_token_cache(access_token)

    return Response(
        content=backend_resp.content,
        status_code=backend_resp.status_code,
        headers=response_headers,
        media_type=backend_resp.headers.get("content-type")
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "services": list(MICROSERVICES.keys())}


@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )