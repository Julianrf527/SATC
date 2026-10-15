"""
IP real del cliente para rate limiting, bloqueo de login y auditoría.

Toda petición externa llega por nginx -> api-gateway -> app-users, así que
`request.client.host` es siempre la IP del contenedor del gateway: usarla como
identidad hace que el límite de login sea uno solo para toda la entidad (los
intentos fallidos de unos bloquean a todos).

El gateway calcula la IP del cliente a partir de `X-Real-IP` (que nginx
SOBREESCRIBE con `$remote_addr`) y la reenvía en `X-Gateway-Client-IP`,
descartando cualquier cabecera homónima que mande el cliente. Aquí solo se
confía en ella si la petición trae un `X-Gateway-Token` válido; en cualquier
otro caso (llamada directa a app-users, token ausente o falso) se usa
`request.client.host` como antes, de modo que una cabecera falsificada no sirve
para repartir intentos entre IPs inventadas.
"""
import hmac
import ipaddress
import os

from dotenv import load_dotenv
from fastapi import Request

load_dotenv()

CLIENT_IP_HEADER = "x-gateway-client-ip"


def _gateway_token_valido(request: Request) -> bool:
    secreto = os.getenv("SECRET_GATEWAY")
    token = request.headers.get("x-gateway-token")
    if not secreto or not token:
        return False
    return hmac.compare_digest(token.encode("utf-8"), secreto.encode("utf-8"))


def obtener_ip_cliente(request: Request) -> str:
    """IP del cliente final, o la del par TCP si no viene del gateway."""
    if _gateway_token_valido(request):
        ip = (request.headers.get(CLIENT_IP_HEADER) or "").strip()
        if ip:
            try:
                return str(ipaddress.ip_address(ip))
            except ValueError:
                pass

    if request.client and request.client.host:
        return request.client.host
    return "unknown"
