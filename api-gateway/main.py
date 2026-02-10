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

NO_CACHE_PATHS = {
    "auth/logout",
    "user/delete",
    "admin/"
}

TOKEN_CACHE = {}
TOKEN_CACHE_TTL = 120
CIRCUIT_BREAKER = {}
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30

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


def decode_jwt_token(access_token: str):
    """
    Decodifica el token JWT y extrae user_id y permisos.
    Retorna un dict con 'user_id' y 'permissions' (lista de nombres de permisos).
    """
    if not access_token:
        raise HTTPException(401, "No token")
    
    try:
        payload = jwt.decode(access_token, SECRET_KEY_GATEWAY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("id")
        permisos = payload.get("permisos", [])
        
        # Extraer solo los nombres de permisos (lista de strings)
        permission_names = [p.get("name") for p in permisos if isinstance(p, dict) and "name" in p]
        
        return {
            "user_id": user_id,
            "permissions": permission_names
        }
    except JWTError as e:
        raise HTTPException(401, f"Invalid token: {str(e)}")


def get_current_user_cached(access_token: str):
    if not access_token:
        raise HTTPException(401, "No token")
    
    if access_token in TOKEN_CACHE:
        cached_data, timestamp = TOKEN_CACHE[access_token]
        if time.time() - timestamp < TOKEN_CACHE_TTL:
            return cached_data
    
    # Decodificar token para obtener user_id y permisos
    token_data = decode_jwt_token(access_token)
    TOKEN_CACHE[access_token] = (token_data, time.time())
    
    if len(TOKEN_CACHE) > 500:
        TOKEN_CACHE.clear()
    
    return token_data


def invalidate_token_cache(access_token: str):
    TOKEN_CACHE.pop(access_token, None)


def get_current_user_smart(access_token: str, path: str):
    if any(path.startswith(critical) for critical in NO_CACHE_PATHS):
        return decode_jwt_token(access_token)
    return get_current_user_cached(access_token)


def is_circuit_open(service: str) -> bool:
    if service not in CIRCUIT_BREAKER:
        return False
    
    failures, last_failure = CIRCUIT_BREAKER[service]
    
    if datetime.now() - last_failure > timedelta(seconds=CIRCUIT_BREAKER_TIMEOUT):
        del CIRCUIT_BREAKER[service]
        return False
    
    return failures >= CIRCUIT_BREAKER_THRESHOLD


def record_failure(service: str):
    if service not in CIRCUIT_BREAKER:
        CIRCUIT_BREAKER[service] = (1, datetime.now())
    else:
        failures, _ = CIRCUIT_BREAKER[service]
        CIRCUIT_BREAKER[service] = (failures + 1, datetime.now())


def record_success(service: str):
    if service in CIRCUIT_BREAKER:
        del CIRCUIT_BREAKER[service]


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(
    service: str, 
    path: str, 
    request: Request, 
    access_token: str = Cookie(None)
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
        token_data = get_current_user_smart(access_token, path)

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
        backend_resp = await http_client.request(
            request.method,
            target_url,
            headers=headers,
            params=request.query_params,
            content=body,
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

    content_length = backend_resp.headers.get("content-length")
    if content_length and int(content_length) > 1_000_000:
        return StreamingResponse(
            backend_resp.aiter_bytes(),
            status_code=backend_resp.status_code,
            headers=response_headers,
            media_type=backend_resp.headers.get("content-type")
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