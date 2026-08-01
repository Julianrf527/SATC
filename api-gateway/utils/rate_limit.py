"""Rate limiting distribuido para el gateway, sobre el Redis de sesiones.

El contador va en Redis y no en memoria porque debe ser compartido entre los 6
workers de Gunicorn: por worker, el límite real sería 6× el configurado y se
reiniciaría en cada redeploy.

Algoritmo: ventana fija (INCR + EXPIRE). Cuesta una clave entera por identidad
y ventana, frente a un sorted set con una entrada por request del
sliding-window-log. Su defecto conocido es el borde de ventana (hasta 2× el
límite concentrando peticiones al final de una ventana y al principio de la
siguiente); para frenar fuerza bruta y abuso automatizado esa imprecisión es
irrelevante.

Identidad del cliente: nginx es el único que alcanza al gateway y fija
`X-Real-IP: $remote_addr`, así que esa cabecera es confiable. `X-Forwarded-For`
es el respaldo y se lee de DERECHA A IZQUIERDA: nginx usa
`$proxy_add_x_forwarded_for`, que anexa la IP real al final de lo que mandó el
cliente, por lo que el último elemento es el único no falsificable. Leer el
primero permitiría saltarse el límite mandando `X-Forwarded-For: <ip-al-azar>`.

Fail-open: si Redis no responde se deja pasar la petición y se loguea. El
control crítico ya falla cerrado por separado (`main.proxy` devuelve 503 si no
puede leer la sesión), así que con Redis caído la superficie autenticada está
igualmente cerrada; lo único que seguiría fluyendo son las rutas públicas y
`/health`. Fallar cerrado acá convertiría un parpadeo de Redis en una caída
total, healthcheck incluido, y reiniciaría el contenedor en bucle.
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("1", "true", "yes")

# Límite general por IP. Deliberadamente holgado: la entidad accede desde
# oficinas detrás de NAT, así que decenas de usuarios legítimos comparten una
# sola IP pública, y el SPA dispara varias peticiones en paralelo por pantalla.
# 600/min (10 rps sostenidos) frena scraping y flood automatizado sin arriesgar
# tráfico real. El estrangulamiento fino va por usuario (LIMITE_USUARIO_MAX).
LIMITE_IP_MAX = int(os.getenv("RATE_LIMIT_IP_MAX", "600"))
LIMITE_IP_VENTANA = int(os.getenv("RATE_LIMIT_IP_WINDOW", "60"))

# Límite por usuario autenticado. Es la dimensión precisa cuando varios
# usuarios comparten IP de salida.
LIMITE_USUARIO_MAX = int(os.getenv("RATE_LIMIT_USER_MAX", "300"))
LIMITE_USUARIO_VENTANA = int(os.getenv("RATE_LIMIT_USER_WINDOW", "60"))

# Límite estricto sobre rutas de autenticación. Complementa al throttle por
# cuenta de app-users: al actuar por IP cubre el password-spraying contra
# muchas cuentas distintas, que un throttle por cuenta no ve. 20 intentos /
# 5 min tolera una oficina tras NAT equivocándose de contraseña y hace inviable
# la fuerza bruta.
LIMITE_AUTH_MAX = int(os.getenv("RATE_LIMIT_AUTH_MAX", "20"))
LIMITE_AUTH_VENTANA = int(os.getenv("RATE_LIMIT_AUTH_WINDOW", "300"))

# Prefijos (relativos al servicio) considerados de autenticación.
PREFIJOS_AUTH = ("auth/login", "auth/recovery")


def obtener_ip_cliente(request) -> str:
    """IP del cliente según las cabeceras que pone nginx.

    `X-Forwarded-For` se lee por la derecha porque nginx anexa la IP real al
    final de lo que envió el cliente (ver docstring del módulo).
    """
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip.strip():
        return real_ip.strip()

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        partes = [p.strip() for p in forwarded.split(",") if p.strip()]
        if partes:
            return partes[-1]

    if request.client and request.client.host:
        return request.client.host

    return "desconocido"


def es_ruta_auth(path: str) -> bool:
    """`path` es lo que va después de `/{service}/`."""
    return any(path == p or path.startswith(p + "/") or path.startswith(p + "-")
               for p in PREFIJOS_AUTH)


async def consumir(redis_client, clave: str, maximo: int, ventana: int) -> Optional[int]:
    """Cuenta una petición contra `clave`.

    Devuelve `None` si la petición está permitida, o los segundos que faltan
    para que se libere la ventana si se excedió el límite.

    Fail-open ante cualquier error de Redis (ver docstring del módulo).
    """
    if not RATE_LIMIT_ENABLED or redis_client is None:
        return None

    try:
        pipe = redis_client.pipeline()
        pipe.incr(clave)
        pipe.ttl(clave)
        contador, ttl = await pipe.execute()

        # TTL negativo = clave recién creada (-1: sin expiración). Se fija acá y
        # no con un EXPIRE incondicional en el pipeline: reiniciar el TTL en
        # cada petición convertiría la ventana fija en un baneo deslizante que
        # solo se libera tras `ventana` segundos de silencio total.
        if ttl is None or ttl < 0:
            await redis_client.expire(clave, ventana)
            ttl = ventana

        if contador > maximo:
            return max(int(ttl), 1)
        return None
    except Exception as e:  # noqa: BLE001 - cualquier fallo de Redis es fail-open
        logger.warning(f"Rate limit no aplicado (Redis no disponible): {e}")
        return None


async def verificar_ip(redis_client, ip: str, path_servicio: str) -> Optional[int]:
    """Aplica el límite general por IP y, si aplica, el estricto de auth.

    El de auth se evalúa primero para que un flood de logins agote la ventana
    corta antes que la general.
    """
    if es_ruta_auth(path_servicio):
        espera = await consumir(
            redis_client, f"ratelimit:auth:{ip}", LIMITE_AUTH_MAX, LIMITE_AUTH_VENTANA
        )
        if espera is not None:
            return espera

    return await consumir(
        redis_client, f"ratelimit:ip:{ip}", LIMITE_IP_MAX, LIMITE_IP_VENTANA
    )


async def verificar_usuario(redis_client, user_id) -> Optional[int]:
    return await consumir(
        redis_client,
        f"ratelimit:user:{user_id}",
        LIMITE_USUARIO_MAX,
        LIMITE_USUARIO_VENTANA,
    )
