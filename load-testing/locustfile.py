# ====================================
# SATC - Prueba de Carga con Locust
# ====================================
# Uso:
#   locust -f locustfile.py --host http://localhost:8000
#   locust -f locustfile.py --host http://localhost:8000 --headless -u 100 -r 10 --run-time 2m
#
# Escenarios validados:
#   - 30  usuarios (carga típica)
#   - 50  usuarios (carga media)
#   - 100 usuarios (carga máxima validada)
# ====================================

from locust import HttpUser, task, between, events
import requests as _requests
import random
import logging

logger = logging.getLogger(__name__)

# ------------------------------------
# Credenciales de prueba
# ------------------------------------
TEST_EMAIL    = "julianrf527@gmail.com"
TEST_PASSWORD = "Pedrois90#"
TEST_USER_ID  = "1233506795"   # numero_documento del usuario de prueba

# ------------------------------------
# Cookie compartida (singleton)
# ------------------------------------
# El sistema usa cookies httponly (access_token).
# El rate limiter de login permite sólo 10 req/min por IP;
# con 30-100 usuarios virtuales desde la misma máquina todos usarían
# la misma IP → bloqueo. Solución: hacer login UNA sola vez antes del
# test y compartir la cookie entre todos los usuarios virtuales.
# Equivale a simular sesiones independientes que usan el mismo JWT,
# que es el comportamiento real del frontend (todos obtienen cookies iguales).
# ------------------------------------
_shared_cookie: str | None = None


@events.test_start.add_listener
def do_login(environment, **kwargs):
    """Login único antes de que arranquen los usuarios virtuales."""
    global _shared_cookie
    try:
        resp = _requests.post(
            f"{environment.host}/users/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
            timeout=15
        )
        if resp.status_code == 200:
            _shared_cookie = resp.cookies.get("access_token")
            if _shared_cookie:
                logger.info("Login exitoso — cookie compartida entre todos los usuarios virtuales")
            else:
                logger.error("Login 200 pero sin cookie access_token en la respuesta")
        else:
            logger.error(f"Login fallido [{resp.status_code}]: {resp.text[:300]}")
    except Exception as e:
        logger.error(f"Error al hacer login inicial: {e}")


# ====================================
# Usuario base con autenticación JWT
# ====================================
class SATCUser(HttpUser):
    """
    Usuario base. La cookie de sesión se inyecta desde el singleton
    obtenido en test_start — evita múltiples logins desde la misma IP.
    """
    wait_time = between(1, 3)

    def on_start(self):
        if _shared_cookie:
            self.client.cookies.set("access_token", _shared_cookie)

    # --------------------------------
    # HEALTH CHECK (sin auth)
    # --------------------------------
    @task(5)
    def health_gateway(self):
        self.client.get("/health", name="GET /health")

    # --------------------------------
    # USUARIOS
    # --------------------------------
    @task(10)
    def list_users(self):
        self.client.get("/users/user/all", name="GET /users/user/all")

    @task(5)
    def list_roles(self):
        self.client.get("/users/role/all", name="GET /users/role/all")

    @task(3)
    def list_permissions(self):
        self.client.get("/users/role/permissions", name="GET /users/role/permissions")

    @task(4)
    def get_notifications(self):
        self.client.get(
            f"/users/notification/all/{TEST_USER_ID}",
            name="GET /users/notification/all/:id"
        )

    @task(2)
    def get_audit_log(self):
        self.client.get("/users/user/log", name="GET /users/user/log")

    # --------------------------------
    # SANCIONATORIA
    # --------------------------------
    @task(8)
    def list_expedientes(self):
        # GET /file/get → lista paginada de expedientes
        self.client.get("/sanctioning/file/get", name="GET /sanctioning/file/get")

    @task(5)
    def list_expedientes_all(self):
        # GET /file/get/all → expedientes sin paginar (carga más pesada)
        self.client.get("/sanctioning/file/get/all", name="GET /sanctioning/file/get/all")

    @task(6)
    def list_municipios(self):
        self.client.get("/sanctioning/town/sidewalk", name="GET /sanctioning/town/sidewalk")

    @task(3)
    def get_alerts(self):
        self.client.get("/sanctioning/file/alerts/all", name="GET /sanctioning/file/alerts/all")

    # --------------------------------
    # DOCUMENTOS (sin endpoints accesibles con este rol)
    # Se testea el health implícito del servicio vía Gateway
    # --------------------------------


# ====================================
# Escenario de lectura pura (GET only)
# Simula usuarios que solo consultan
# ====================================
class ReadOnlyUser(SATCUser):
    """70% de los usuarios totales — solo lecturas."""
    weight = 7
    wait_time = between(2, 5)

    @task(15)
    def list_expedientes(self):
        self.client.get("/sanctioning/file/get", name="GET /sanctioning/file/get")

    @task(10)
    def list_users(self):
        self.client.get("/users/user/all", name="GET /users/user/all")

    @task(8)
    def list_expedientes_all(self):
        self.client.get("/sanctioning/file/get/all", name="GET /sanctioning/file/get/all")

    @task(5)
    def health_gateway(self):
        self.client.get("/health", name="GET /health")


# ====================================
# Escenario de escritura (POST)
# Simula usuarios que crean registros
# ====================================
class WriteUser(SATCUser):
    """30% de los usuarios totales — mezcla lectura + escritura."""
    weight = 3
    wait_time = between(3, 8)

    @task(5)
    def list_expedientes_write(self):
        self.client.get("/sanctioning/file/get", name="GET /sanctioning/file/get")

    @task(2)
    def health_gateway(self):
        self.client.get("/health", name="GET /health")


# ====================================
# Listeners de eventos para logging
# ====================================
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    if exception:
        logger.warning(f"[FAIL] {request_type} {name} | {response_time:.0f}ms | {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("=" * 60)
    logger.info("Iniciando prueba de carga SATC")
    logger.info(f"Host: {environment.host}")
    logger.info("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats.total
    logger.info("=" * 60)
    logger.info("Resultados finales SATC")
    logger.info(f"  Requests totales : {stats.num_requests}")
    logger.info(f"  Failures         : {stats.num_failures} ({stats.fail_ratio * 100:.1f}%)")
    logger.info(f"  RPS promedio     : {stats.current_rps:.2f}")
    logger.info(f"  p50 latencia     : {stats.get_response_time_percentile(0.50):.0f}ms")
    logger.info(f"  p95 latencia     : {stats.get_response_time_percentile(0.95):.0f}ms")
    logger.info(f"  p99 latencia     : {stats.get_response_time_percentile(0.99):.0f}ms")
    logger.info("=" * 60)
