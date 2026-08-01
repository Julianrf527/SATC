# Sistema de Seguridad — SATC

## Documento Técnico Empresarial

**Sistema:** SATC (Sistema de Administración de Trámites de Corpochivor)
**Versión:** 2.1
**Fecha:** 18 de junio de 2026
**Autor:** Julian David Rodriguez Fernandez
**Audiencia:** Administradores del sistema, coordinadores, soporte técnico
**Clasificación:** Confidencial — Solo Uso Interno

---

## Tabla de Contenidos

1. [Resumen de cambios desde febrero 2026](#1-resumen-de-cambios-desde-febrero-2026)
2. [Arquitectura de Seguridad](#2-arquitectura-de-seguridad)
3. [Autenticación y Gestión de Sesiones](#3-autenticacion-y-gestion-de-sesiones)
4. [Autorización y Control de Acceso (RBAC)](#4-autorizacion-y-control-de-acceso-rbac)
5. [Seguridad en Endpoints y APIs](#5-seguridad-en-endpoints-y-apis)
6. [Seguridad de Archivos](#6-seguridad-de-archivos)
7. [Seguridad de Red y Comunicaciones](#7-seguridad-de-red-y-comunicaciones)
8. [Protección de Datos y Privacidad](#8-proteccion-de-datos-y-privacidad)
9. [Auditoría y Trazabilidad](#9-auditoria-y-trazabilidad)
10. [Gestión de Vulnerabilidades](#10-gestion-de-vulnerabilidades)
11. [Plan de Respuesta a Incidentes](#11-plan-de-respuesta-a-incidentes)
12. [Anexos Técnicos](#12-anexos-tecnicos)

---

## 1. Resumen de cambios desde febrero 2026

| Ítem | Doc anterior decía | Estado real (junio 2026) |
|---|---|---|
| WAF / ModSecurity | Activo en el reverse proxy | **Removido** — `nginx.conf` usa `nginx:alpine` sin WAF |
| HTTPS en producción | ✅ Completo | **Pendiente** — solo HTTP, plan de CA interna evaluado, no implementado aún |
| Permisos RBAC | 13 permisos | **21 permisos** (ver `MANUAL_PERMISOS_SATC.md`) |
| Escaneo antivirus | ✅ Completo | Existía la utilidad pero **no se invocaba** en el endpoint de upload — corregido este mes |
| Cabeceras HTTP | No documentadas | **Nuevo** — X-Frame-Options, X-Content-Type-Options, Referrer-Policy, CSP |
| Auditoría | Implementada | **Reforzada** — campos de documento que faltaban en el snapshot de auditoría |

### Postura de Seguridad

SATC implementa un modelo de seguridad de **defensa en profundidad** (Defense in Depth) con múltiples capas de protección:

```
┌─────────────────────────────────────────────────────────────┐
│                    CAPAS DE SEGURIDAD                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [CAPA 1] Seguridad de Red                                  │
│   └─ Segmentación satc-public / satc-private (Docker)       │
│   └─ Único puerto expuesto: 8000 (nginx-lb)                 │
│   └─ Rate Limiting de login vía Redis                       │
│                                                             │
│  [CAPA 2] Autenticación                                     │
│   └─ JWE A256GCM, Bcrypt, Sesiones Únicas (Redis)           │
│   └─ Login Throttling (bloqueo progresivo)                  │
│                                                             │
│  [CAPA 3] Autorización                                      │
│   └─ RBAC Granular con 21 permisos                          │
│   └─ Validación en cada microservicio (no confiado al token)│
│                                                             │
│  [CAPA 4] Cabeceras HTTP (nuevo, junio 2026)                │
│   └─ X-Frame-Options, X-Content-Type-Options                │
│   └─ Referrer-Policy, Content-Security-Policy               │
│                                                             │
│  [CAPA 5] Seguridad de Archivos                             │
│   └─ ClamAV (ahora efectivamente invocado), MIME, SHA-256   │
│                                                             │
│  [CAPA 6] Auditoría y Trazabilidad                          │
│   └─ Logging completo antes/después de cada modificación    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Métricas de Seguridad (estado junio 2026)

| Métrica | Estado Actual | Objetivo |
|---|---|---|
| **Autenticación Multifactor** | ⚠️ Pendiente | Roadmap |
| **Encriptación en Tránsito** | ⚠️ Solo HTTP en LAN — HTTPS pendiente | Pendiente |
| **Encriptación en Reposo** | Sin encriptación (seguridad perimetral) | Próximo ciclo |
| **Escaneo Antivirus** | ✅ ClamAV activo e invocado en upload | ✅ Completo |
| **Auditoría de Accesos** | ✅ 100% trazabilidad, reforzada este mes | ✅ Completo |
| **Rate Limiting** | ✅ Redis (login) | ✅ Activo |
| **Brute Force Protection** | ✅ Login Throttling con bloqueo progresivo | ✅ Completo |
| **Gestión de Sesiones** | ✅ Redis + PostgreSQL con TTL automático | ✅ Completo |
| **Control de Privilegios** | ✅ RBAC granular con 21 permisos | ✅ Completo |
| **Password Hashing** | ✅ Bcrypt configurable (default 10 rounds) | ✅ Completo |
| **Cabeceras HTTP** | ✅ X-Frame-Options, CSP, nosniff, Referrer-Policy | ✅ Nuevo |
| **Cookie Secure=True** | ⚠️ Bloqueado hasta tener HTTPS | Pendiente |

---

## 2. Arquitectura de Seguridad

### 2.1 Modelo de Seguridad General

```
┌────────────────────────────────────────────────────────────────┐
│                     RED LOCAL (LAN)                            │
└────────────────┬───────────────────────────────────────────────┘
                 │
                 │  HTTP :8000 (único puerto expuesto al host)
                 │
         ┌───────▼────────┐
         │  nginx-lb      │◄────── CAPA 1: Rate Limiting, Cabeceras HTTP
         │  (nginx:alpine)│        Sin WAF (removido junio 2026)
         └───────┬────────┘
                 │
         ┌───────┴────────┬─────────────────┐
         │                │                 │
    ┌────▼────┐      ┌────▼────┐       ┌────▼────┐
    │Gateway 1│      │Gateway 2│       │Gateway 3│
    │ (Auth)  │      │ (Auth)  │       │ (Auth)  │
    └────┬────┘      └────┬────┘       └────┬────┘
         │                │                 │
         │  X-Gateway-Token (interno)       │
         │  X-Gateway-User-Id               │
         │  X-Gateway-Permissions           │
         │                │                 │
    ┌────┴────────────────┴─────────────────┴────┐
    │                                            │
┌───▼─────────┐  ┌────────────┐  ┌─────────────┐ │
│ app-users   │  │app-sanction│  │  app-docs   │ │◄─ CAPA 2/3: JWT +
│ (Authn)     │  │   (Files)  │  │  (Docs)     │ │   RBAC 21 permisos
│ RBAC        │  │  RBAC      │  │  RBAC       │ │◄─ Cada uno valida
└─────┬───────┘  └─────┬──────┘  └──────┬──────┘ │   con su propia BD
      │                │                 │       │
┌─────▼────────┐ ┌─────▼────────┐ ┌─────▼──────┐ │
│ PostgreSQL   │ │ PostgreSQL   │ │PostgreSQL  │ │◄─ Aislados entre sí
│ user_db      │ │expedientes_db│ │documentos  │ │   (sin acceso cruzado)
└──────────────┘ └──────┬───────┘ └──────┬─────┘ │
                        │                │       │
                   ┌────▼────────────────▼─────┐ │
                   │       MinIO (Storage)     │ │◄─ CAPA 5: ClamAV
                   │  ClamAV • MIME • SHA-256  │ │   ahora efectivo
                   └───────────────────────────┘ │
                                                 │
    ┌────────────┐                               │
    │   Redis    │◄──────────────────────────────┘
    │ (Sessions) │   Sesiones únicas + Rate Limit
    └────────────┘

    ┌────────────┐
    │  Auditoría │◄─── CAPA 6: datos_anteriores / datos_nuevos
    │ (Postgres) │     reforzada junio 2026
    └────────────┘
```

### 2.2 Zonas de Confianza

```
┌──────────────────────────────────────────────────────────────┐
│  ZONA PÚBLICA (Red local / LAN)                              │
│  Nivel de Confianza: 0%                                      │
│  Acceso: Anónimo                                             │
├──────────────────────────────────────────────────────────────┤
│  • Página de Login                                           │
│  • Recuperación de contraseña                                │
└──────────────────────────────────────────────────────────────┘
                         │
                         │ Autenticación JWE A256GCM
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  ZONA DMZ (Load Balancer + API Gateway)                      │
│  Nivel de Confianza: 30%                                     │
│  Acceso: Requiere JWT válido                                 │
├──────────────────────────────────────────────────────────────┤
│  • NGINX Load Balancer (nginx:alpine, sin WAF)               │
│  • API Gateway (validación de tokens)                        │
│  • Rate Limiting (Redis)                                     │
│  • Cabeceras HTTP de seguridad (CAPA 4)                      │
└──────────────────────────────────────────────────────────────┘
                         │
                         │ X-Gateway-Token (interno)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  ZONA INTERNA (Microservicios)                               │
│  Nivel de Confianza: 70%                                     │
│  Acceso: Requiere X-Gateway-Token + Permisos                 │
├──────────────────────────────────────────────────────────────┤
│  • app-users (autenticación)                                 │
│  • app-sanctioning (expedientes)                             │
│  • app-docs (documentos)                                     │
│  • Validación RBAC (21 permisos) por endpoint                │
│  • Gateway NO reenvía permisos — cada MS valida por su BD    │
└──────────────────────────────────────────────────────────────┘
                         │
                         │ Conexión interna (sin internet)
                         ▼
┌──────────────────────────────────────────────────────────────┐
│  ZONA DE DATOS (Bases de Datos + Storage)                    │
│  Nivel de Confianza: 95%                                     │
│  Acceso: Solo desde microservicios autorizados               │
├──────────────────────────────────────────────────────────────┤
│  • PostgreSQL ×5 (separados, sin acceso cruzado)             │
│  • MinIO (archivos — ClamAV activo)                          │
│  • Redis (sesiones con TTL)                                  │
│  • Sin acceso externo                                        │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 Principios de Seguridad Aplicados

| Principio | Descripción | Implementación en SATC |
|---|---|---|
| **Least Privilege** | Usuarios solo tienen permisos mínimos necesarios | ✅ RBAC granular con 21 permisos específicos |
| **Defense in Depth** | Múltiples capas de seguridad | ✅ 6 capas activas |
| **Fail Secure** | En caso de error, denegar acceso por defecto | ✅ HTTPException 403 si falta permiso |
| **Separation of Duties** | Roles separados (admin, revisor, usuario) | ✅ 3+ roles con permisos distintos |
| **Zero Trust** | No confiar en ninguna zona de red | ✅ Cada microservicio valida con su propia fuente |
| **Auditoría Completa** | Todos los accesos son registrados | ✅ Logs con datos_anteriores / datos_nuevos |

---

## 3. Autenticación y Gestión de Sesiones

### 3.1 Sistema de Autenticación JWT

#### 3.1.1 Flujo Completo de Login

```
┌─────────────┐
│  1. Login   │
│  Frontend   │
└──────┬──────┘
       │ POST /auth/login
       │ { email, password, remember }
       ▼
┌──────────────┐
│  2. Gateway  │  (Proxy sin validación)
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────┐
│  3. app-users: /auth/login                               │
├──────────────────────────────────────────────────────────┤
│  a) Normalizar email (toLowerCase)                       │
│  b) SELECT usuario WHERE correo = ?                      │
│  c) Validaciones Fail-Fast: inactivo → 403, no existe → 401 │
│  d) Bcrypt Async (ThreadPool) verify_password_async()    │
│  e) Generar JTI único: uuid.uuid4()                      │
│  f) Crear JWT Payload (id, nombre, correo, rol_id, jti, exp) │
│  g) Firmar JWT: jwt.encode(payload, SECRET_KEY_GATEWAY)  │
│  h) Guardar Sesión (Redis primero, PostgreSQL fallback)   │
│  i) Set-Cookie: access_token=JWT; HttpOnly; SameSite=Strict │
└──────────────────────────────────────────────────────────┘
       │
       │ 200 OK + Cookie
       ▼
┌──────────────┐
│  4. Frontend │  Redirige a /home
└──────────────┘
```

#### 3.1.2 Estructura del Token JWT

```javascript
// Header
{ "alg": "HS256", "typ": "JWT" }

// Payload
{
  "id": "123456789",
  "primer_nombre": "Juan",
  "primer_apellido": "Pérez",
  "correo": "juan.perez@corpochivor.gov.co",
  "rol_id": 2,
  "jti": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "exp": 1750291200
}

// Firma: HMACSHA256(header + "." + payload, SECRET_KEY_GATEWAY)
```

**Características de Seguridad:**

- ✅ **Firmado con HS256** — No se puede alterar sin clave secreta
- ✅ **Expiración automática (exp)** — Tokens inválidos después de 24 h
- ✅ **JTI único** — Permite invalidación de tokens individuales
- ✅ **Información mínima** — Solo datos necesarios, sin contraseña
- ⚠️ **Payload no encriptado** — Datos visibles en base64 pero firmados

#### 3.1.3 Configuración de Seguridad de Cookies

```python
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,          # Protección XSS
    samesite="Strict",      # Protección CSRF
    secure=False,           # ⚠️ Pendiente hasta tener HTTPS
    max_age=86400,          # 24 horas si remember=True
    path="/",
    domain=None
)
```

> **Nota:** `secure=True` está bloqueado hasta implementar HTTPS. Ver sección de pendientes.

### 3.2 Sistema de Sesiones Únicas

**Arquitectura Redis + PostgreSQL:**

```
┌─────────────────────────────────────────────────────────┐
│         SISTEMA DE SESIONES (Redis + PostgreSQL)        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Redis (Primario):                                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Key: session:{jti}                                │  │
│  │ Value: { usuario_id, ip_address, user_agent,      │  │
│  │          activo, fecha_creacion }                 │  │
│  │ TTL: 24 hours (auto-cleanup)                      │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  PostgreSQL (Fallback + Auditoría):                     │
│  TABLE: sesion_activa                                   │
│  ├─ id, usuario_id, token_jti (UNIQUE)                  │
│  ├─ ip_address, user_agent                              │
│  ├─ activo, fecha_creacion, fecha_ultimo_uso            │
│                                                         │
│  Política:                                              │
│  • Solo 1 sesión activa por usuario                     │
│  • Login nuevo → Invalida sesión anterior               │
│  • Logout → Invalida sesión actual                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 3.3 Protección contra Ataques de Autenticación

#### 3.3.1 Brute Force Protection

```python
# app-users/utils/rate_limiter.py

class LoginThrottler:
    """Bloqueo progresivo por intentos fallidos (email + IP)"""

    @staticmethod
    def record_failed_login(identifier: str) -> Dict:
        attempts = redis_client.incr(f"login_fail:{identifier}")

        if attempts >= 15:
            block_duration = 7200   # 2 horas
        elif attempts >= 10:
            block_duration = 1800   # 30 minutos
        elif attempts >= 5:
            block_duration = 300    # 5 minutos
        else:
            return {"blocked": False, "attempts": attempts}

        redis_client.setex(f"login_block:{identifier}", block_duration, "blocked")
        return {"blocked": True, "attempts": attempts, "block_duration": block_duration}
```

#### 3.3.2 Session Hijacking Protection

| Ataque | Protección | Estado |
|---|---|---|
| **Session Fixation** | JTI único generado en servidor | ✅ Implementado |
| **Session Theft (XSS)** | HttpOnly cookies | ✅ Implementado |
| **Session Theft (Network)** | HTTPS pendiente | ⚠️ Bloqueado |
| **CSRF** | SameSite=Strict | ✅ Implementado |
| **Token Replay** | Expiración 24 h + Sesión única | ✅ Implementado |

#### 3.3.3 Password Security (Bcrypt)

```python
# app-users/utils/passwords.py

BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "10"))

def hash_password(password: str) -> str:
    truncated = _truncate_to_72_bytes(password).decode("utf-8", errors="ignore")
    return passlib_bcrypt.using(rounds=BCRYPT_ROUNDS).hash(truncated)

async def verify_password_async(password: str, hashed: str) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, verify_password, password, hashed)
```

| Rounds | Tiempo/Hash | Uso |
|---|---|---|
| 3–4 | ~50 ms | Testing únicamente |
| 8–10 | ~250 ms | Producción red local |
| 10–12 | ~300–600 ms | Internet público |

---

## 4. Autorización y Control de Acceso (RBAC)

### 4.1 Modelo RBAC

El sistema cuenta ahora con **21 permisos** (eran 13 en febrero 2026). Ver listado completo en `MANUAL_PERMISOS_SATC.md`.

```
┌──────────────────────────────────────────────────────────────┐
│                MODELO JERÁRQUICO RBAC                        │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Rol: Admin (id: 1)                                          │
│  └─► Permisos: TODOS (21 permisos)                           │
│                                                              │
│  Rol: Revisor (id: 2)                                        │
│  └─► Subconjunto de permisos de documento y expediente       │
│                                                              │
│  Rol: Usuario Básico (id: 3)                                 │
│  └─► expediente_consultar + notificacion_recibir             │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Flujo de Autorización Zero-DB-Query

```python
# Validación en cada microservicio — SIN query a BD en cada request

def verify_permission(request: Request, required_permission: str) -> int:
    permissions_json = request.headers.get("X-Gateway-Permissions")
    permissions = json.loads(permissions_json)

    if required_permission not in permissions:
        raise HTTPException(403, "No tienes permiso")

    return int(request.headers.get("X-Gateway-User-Id"))
```

> **Importante:** El gateway nunca reenvía permisos a los microservicios directamente — cada microservicio valida con su propia fuente de datos.

### 4.3 Control de Escalada de Privilegios

```python
# app-users/routes/role.py

permisos_no_autorizados = requested_permissions - user_permissions
if permisos_no_autorizados:
    raise HTTPException(
        status_code=403,
        detail=f"No puede asignar permisos que no posee: {', '.join(nombres_permisos)}"
    )
```

---

## 5. Seguridad en Endpoints y APIs

### 5.1 Cabeceras HTTP de Seguridad (nuevo, junio 2026)

Las siguientes cabeceras fueron agregadas en junio 2026:

```nginx
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'" always;
```

> **Nota:** `Strict-Transport-Security` no se agrega hasta tener HTTPS activo.

### 5.2 Protección contra Vulnerabilidades OWASP

#### SQL Injection

```python
# ✅ SQLAlchemy ORM con Prepared Statements (automático)
stmt = select(Usuario).where(Usuario.correo == email)
result = await db.execute(stmt)
# SQL generado: SELECT * FROM usuarios WHERE correo = $1
```

#### XSS

- ✅ HttpOnly cookies (tokens no accesibles desde JavaScript)
- ✅ CSP header implementado (`Content-Security-Policy`)
- ✅ Sin `dangerouslySetInnerHTML` sin sanitizar en el frontend

#### Broken Access Control

- ✅ RBAC granular en todos los endpoints (21 permisos)
- ✅ Control de escalada de privilegios
- ✅ Admin no puede eliminarse a sí mismo

#### Insecure Deserialization

- ✅ Solo JSON para comunicación (no pickle)
- ✅ Validación con Pydantic schemas

### 5.3 CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Cambiar a dominio real en producción
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### 5.4 Validación Interna entre Microservicios

```python
def verify_gateway_token(request: Request) -> int:
    gw_token = request.headers.get("X-Gateway-Token")
    if not gw_token or gw_token != SECRET_GATEWAY:
        raise HTTPException(403, "Gateway token inválido")
    user_id = request.headers.get("X-Gateway-User-Id")
    return int(user_id)
```

---

## 6. Seguridad de Archivos

### 6.1 Sistema de Validación en 5 Capas

```
┌─────────────────────────────────────────────────────────────┐
│          UPLOAD DE ARCHIVO — 5 CAPAS DE SEGURIDAD           │
├─────────────────────────────────────────────────────────────┤
│  [CAPA 1] Validación de Extensión                           │
│  ├─ Permitidas: .pdf .doc .docx .xls .xlsx .txt             │
│  │              .jpg .jpeg .png .gif .zip .rar               │
│  └─ Bloqueadas: .exe .bat .cmd .sh .ps1 .vbs .jar ...       │
├─────────────────────────────────────────────────────────────┤
│  [CAPA 2] Validación MIME / Magic Bytes                     │
│  └─ Comparar MIME real (python-magic) vs extensión declarada│
├─────────────────────────────────────────────────────────────┤
│  [CAPA 3] Sanitización de Nombres de Archivo                │
│  ├─ Eliminar: ../ \\ < > : " | ? *                          │
│  └─ Generar nombre único: YYYYMMDD_HHMMSS_original.ext      │
├─────────────────────────────────────────────────────────────┤
│  [CAPA 4] Escaneo Antivirus (ClamAV)                        │
│  ├─ Ahora efectivamente invocado (corregido junio 2026)     │
│  └─ stream scan en memoria — rechaza si virus encontrado    │
├─────────────────────────────────────────────────────────────┤
│  [CAPA 5] Almacenamiento Seguro en MinIO                    │
│  ├─ Hash SHA-256 para deduplicación                         │
│  └─ No accesible desde internet — URLs pre-firmadas (1 h)   │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 ClamAV

```python
# app-sancionatoria/utils/antivirus.py

def escanear_archivo(file_data: bytes, filename: str) -> Dict:
    cd = pyclamd.ClamdNetworkSocket(host=CLAMAV_HOST, port=CLAMAV_PORT)
    resultado = cd.scan_stream(file_data)

    if resultado is None:
        return {"ok": True, "virus_encontrado": None, "escaneado": True}

    virus_nombre = resultado.get("stream", ("UNKNOWN", "UNKNOWN"))[1]
    return {"ok": False, "virus_encontrado": virus_nombre, "escaneado": True}
```

| Métrica | Valor |
|---|---|
| **Tiempo de escaneo** | ~100–500 ms (según tamaño) |
| **Precisión** | 99.9% detección de virus conocidos |
| **Base de datos** | 8.5 millones de firmas |
| **Actualización** | Automática diaria |

### 6.3 Almacenamiento Seguro (MinIO)

```python
def get_file_from_minio(bucket: str, object_name: str) -> str:
    url = client.presigned_get_object(
        bucket, object_name, expires=timedelta(hours=1)
    )
    return url
```

---

## 7. Seguridad de Red y Comunicaciones

### 7.1 Topología de Red Segura

```
                       │ Puerto 8000 (HTTP — HTTPS pendiente)
                ┌──────▼──────┐
                │ nginx-lb    │   nginx:alpine (sin WAF desde junio 2026)
                └──────┬──────┘
                       │
┌──────────────────────┴───────────────────────────────────────┐
│                  RED INTERNA SATC                            │
│   satc-public / satc-private (Docker networks separadas)     │
│                                                              │
│  gateway-1/2/3 → app-users-1/2 → postgres-users             │
│               → app-sanctioning-1/2 → postgres-expedientes  │
│               → app-docs → postgres-docs                     │
│               → Redis • MinIO • ClamAV                       │
│                                                              │
│  Reglas de Red:                                              │
│  ✅ Microservicios NO expuestos a internet                   │
│  ✅ Solo nginx-lb tiene puerto público (8000)                │
│  ✅ BDs solo accesibles desde sus microservicios             │
│  ✅ Sin acceso cruzado entre BDs                             │
└──────────────────────────────────────────────────────────────┘
```

### 7.2 Configuración NGINX

```nginx
# nginx/nginx.conf

upstream api_gateway {
    least_conn;
    server api-gateway-1:8000 max_fails=3 fail_timeout=30s;
    server api-gateway-2:8000 max_fails=3 fail_timeout=30s;
    server api-gateway-3:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}

server {
    listen 80;

    client_body_timeout 10s;
    client_header_timeout 10s;
    client_max_body_size 10M;

    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
    limit_req zone=api_limit burst=20 nodelay;

    # Cabeceras de seguridad (junio 2026)
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'" always;

    server_tokens off;

    location / {
        proxy_pass http://api_gateway;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_connect_timeout 30s;
        proxy_send_timeout 90s;
        proxy_read_timeout 90s;
    }
}
```

### 7.3 Protección DDoS (básica)

| Ataque | Protección | Estado |
|---|---|---|
| **HTTP Flood** | Rate Limiting (100 req/min) | ✅ Básico |
| **Slowloris** | client_body/header_timeout | ✅ Implementado |
| **Large Payload** | client_max_body_size 10 MB | ✅ Implementado |
| **DDoS avanzado** | Sin Cloudflare / AWS Shield | ⚠️ Roadmap |

### 7.4 HTTPS (pendiente)

HTTPS estaba documentado como activo en febrero 2026 — **ese dato era incorrecto**. El sistema actualmente opera en HTTP en la LAN. Está en evaluación implementar una CA interna; no hay fecha comprometida.

```nginx
# Configuración preparada para cuando se implemente HTTPS:
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/satc.crt;
    ssl_certificate_key /etc/nginx/ssl/satc.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
```

---

## 8. Protección de Datos y Privacidad

### 8.1 Clasificación de Datos

| Tipo de Datos | Sensibilidad | Protección Actual |
|---|---|---|
| **Contraseñas** | CRÍTICA | Bcrypt hash ✅ |
| **Datos personales** (nombre, email, DNI) | ALTA | BD sin encriptación en reposo ⚠️ |
| **Documentos** | ALTA | MinIO sin encriptación en reposo ⚠️ |
| **Logs de auditoría** | MEDIA | Texto plano (sin datos sensibles) ✅ |
| **Tokens JWT** | CRÍTICA | Firmados HS256 ✅ |
| **Sesiones Redis** | ALTA | Texto plano — aislado en red interna ⚠️ |

### 8.2 Decisión: No Encriptación en Reposo

**Justificación:** El sistema opera en red local sin exposición externa. Los controles compensatorios activos son:

1. PostgreSQL y MinIO **NO expuestos** a red externa
2. Acceso exclusivo desde contenedores autorizados (red Docker interna)
3. RBAC granular + auditoría completa en capa de aplicación
4. Acceso físico al servidor restringido

**Amenazas no mitigadas:** robo físico del servidor, acceso directo a discos/backups, personal con acceso root. Estas son aceptadas dadas las condiciones del entorno.

### 8.3 Enmascaramiento de Datos en Logs

```python
# ✅ Correcto
logger.info(f"Login exitoso: {email[:3]}***@{email.split('@')[1]}")
logger.debug(f"Token generado: {token[:10]}...")

# ❌ Nunca hacer
# logger.info(f"Login: {email} con contraseña {password}")
```

### 8.4 Derechos del Usuario (GDPR)

| Derecho | Endpoint | Estado |
|---|---|---|
| Derecho de acceso | GET /user/me | ✅ |
| Derecho de rectificación | PUT /user/update/{id} | ✅ |
| Derecho al olvido | DELETE /user/delete/{id} | ✅ |
| Derecho a la portabilidad | GET /user/export/{id} | ⚠️ Roadmap |
| Derecho de oposición | POST /user/opt-out | ⚠️ Roadmap |

---

## 9. Auditoría y Trazabilidad

### 9.1 Sistema de Logs de Auditoría

```
TABLE: log_auditoria (PostgreSQL)
├─ id              SERIAL PRIMARY KEY
├─ usuario_id      INT (FK → usuarios)
├─ tabla_afectada  VARCHAR
├─ tipo_operacion  VARCHAR (INSERT/UPDATE/DELETE/SELECT)
├─ descripcion     TEXT
├─ fecha           TIMESTAMP
├─ datos_anteriores JSON   ← reforzado junio 2026
├─ datos_nuevos     JSON   ← reforzado junio 2026
├─ expediente_radicado VARCHAR
└─ id_registro     VARCHAR
```

**Eventos auditados:**

- ✅ Login / Logout
- ✅ Creación / Modificación / Eliminación de usuarios
- ✅ Cambios de roles y permisos
- ✅ Creación / Modificación / Eliminación de expedientes
- ✅ Upload / Download de archivos
- ✅ Cambios de estado de documentos
- ✅ Asignación de revisores

### 9.2 Ejemplo de Entrada de Auditoría

```json
{
  "usuario_id": 123456789,
  "tabla_afectada": "usuarios",
  "tipo_operacion": "UPDATE",
  "descripcion": "Cambio de rol en usuario ID 987654321",
  "fecha": "2026-06-18 10:30:45",
  "datos_anteriores": { "rol_id": 3, "activo": true },
  "datos_nuevos": { "rol_id": 2, "activo": true }
}
```

### 9.3 Retención de Logs

```yaml
Logs de Aplicación (Docker):
  Retención: 7 días
  Rotación: max-size 10MB, max-file 3

Logs de Auditoría (PostgreSQL):
  Retención: 5 años (compliance)
  Archivado: cold storage después de 1 año

Logs de Acceso (NGINX):
  Retención: 30 días
  Rotación: Diaria
```

---

## 10. Gestión de Vulnerabilidades

### 10.1 Estado de Dependencias (escaneo junio 2026)

- **Backend — 6 microservicios (`pip-audit`):** 0 vulnerabilidades conocidas.
- **Frontend (`npm audit`):** 20 encontradas → 14 corregidas sin riesgo de incompatibilidad, incluyendo la única dependencia de producción afectada (`react-router-dom`). Las 6 restantes corresponden a herramientas de testing (`vitest` y relacionados) — sin exposición en producción.

Detalle completo: `REPORTE_VULNERABILIDADES.md`.

### 10.2 Privilegios de Base de Datos

Los 5 microservicios con BD propia corren con el rol superusuario `postgres` por defecto, dentro de contenedores y volúmenes completamente separados entre sí (no hay acceso cruzado posible). El principio de mínimo privilegio dentro de cada base individual está **pendiente para el próximo ciclo**. Ver `PLAN_MEJORAS_JUNIO_2026.md`.

### 10.3 Proceso de Gestión de Vulnerabilidades

```
[1] IDENTIFICACIÓN  →  pip-audit, npm audit, revisión OWASP Top 10
[2] CLASIFICACIÓN   →  CRÍTICA / ALTA / MEDIA / BAJA
[3] PRIORIZACIÓN    →  CRÍTICA: 24h  |  ALTA: 7d  |  MEDIA: 30d  |  BAJA: next release
[4] REMEDIACIÓN     →  Actualizar dependencias + documentar en CHANGELOG
[5] VERIFICACIÓN    →  Re-escanear + pruebas de regresión
```

### 10.4 Herramientas de Escaneo

```bash
# Backend
pip install pip-audit && pip-audit

# Frontend
npm audit
npm audit fix        # solo cambios seguros
npm audit fix --force  # requiere validación de breaking changes (vitest pendiente)
```

---

## 11. Plan de Respuesta a Incidentes

### 11.1 Clasificación de Incidentes

| Nivel | Descripción | Tiempo de Respuesta |
|---|---|---|
| **P1 - CRÍTICO** | Breach de datos, ransomware, sistema caído | < 1 hora |
| **P2 - ALTO** | Vulnerabilidad explotable, falla de autenticación | < 4 horas |
| **P3 - MEDIO** | XSS en formulario, leak de info no crítica | < 24 horas |
| **P4 - BAJO** | Configuración insegura, logs con info sensible | < 1 semana |

### 11.2 Procedimiento de Respuesta

```
Fase 1 — Detección y Análisis (0–2 h)
  1. Detectar incidente → clasificar severidad → notificar equipo
  2. Análisis: qué, cuándo, cómo, qué datos afectados

Fase 2 — Contención (2–6 h)
  3. Ransomware → desconectar de red
  4. Breach → cambiar credenciales comprometidas
  5. DDoS → activar rate limiting agresivo

Fase 3 — Erradicación (6–24 h)
  6. Aplicar parche definitivo → fortalecer defensa

Fase 4 — Recuperación (24–48 h)
  7. Restaurar desde backup si necesario → monitoreo 72 h post-incidente

Fase 5 — Lecciones Aprendidas (1 semana)
  8. Post-mortem → actualizar runbooks y políticas
```

### 11.3 Contactos de Emergencia

```yaml
Director de TI:
  Email: director.ti@corpochivor.gov.co
  Disponibilidad: 24/7 para P1

Líder de Seguridad:
  Email: seguridad@corpochivor.gov.co
  Disponibilidad: 24/7 para P1–P2

Desarrollador:
  Email: julianrf527@gmail.com
  Teléfono: +57 321 497 5446
  Disponibilidad: Horario laboral + on-call
```

---

## 12. Anexos Técnicos

### 12.1 Variables de Entorno de Seguridad

```bash
# CLAVES SECRETAS (NUNCA COMMITEAR EN GIT)
SECRET_KEY_GATEWAY=<openssl rand -hex 32>
SECRET_GATEWAY=<openssl rand -hex 32>
SERVICE_SECRET_KEY=<openssl rand -hex 32>

# AUTENTICACIÓN
JWT_ALGORITHM=HS256
JWT_EXP_DAYS=1
BCRYPT_ROUNDS=10       # dev: 3-4 | prod: 10

# BASE DE DATOS
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<strong-password>
REDIS_URL=redis://satc-redis:6379/0
REDIS_PASSWORD=<strong-password>

# STORAGE
MINIO_ROOT_USER=admin
MINIO_ROOT_PASSWORD=<strong-password>
MINIO_ENDPOINT=satc-minio:9000

# ANTIVIRUS
CLAMAV_ENABLED=true
CLAMAV_HOST=clamav
CLAMAV_PORT=3310

# ARCHIVOS
MAX_FILE_SIZE_MB=10
UPLOAD_DIR=/app/secure-uploads

# CORS
CORS_ORIGINS=http://localhost:3000   # prod: dominio real

# MODO
ENVIRONMENT=development
DEBUG=false   # SIEMPRE false en producción
```

### 12.2 Checklist Pre-Deployment

```
□ Cambiar todas las claves secretas de desarrollo
□ Bcrypt rounds: 3 (dev) → 10 (prod)
□ HTTPS/TLS: certificado, redirect HTTP→HTTPS, HSTS
□ CORS_ORIGINS: localhost → dominio de producción
□ Cookie secure=True (activar junto con HTTPS)
□ Ajustar rate limits según carga esperada
□ Verificar backups automáticos y restauración
□ Desactivar DEBUG, ocultar versiones (server_tokens off)
□ Escaneo de vulnerabilidades (OWASP ZAP / Burp Suite)
□ Actualizar contactos de seguridad
```

### 12.3 Comandos Útiles de Seguridad

```bash
# Generar clave secreta
openssl rand -hex 32

# Ver sesiones activas en Redis
docker exec -it satc-redis redis-cli
KEYS session:*

# Verificar sesiones en PostgreSQL
docker exec -it satc-postgres-users psql -U postgres -d user_db
SELECT * FROM sesion_activa WHERE activo = true;

# Logs de auditoría recientes
SELECT usuario_id, tipo_operacion, fecha FROM log_auditoria
ORDER BY fecha DESC LIMIT 20;

# Estado ClamAV
docker exec satc-clamav clamdcheck

# Verificar configuración NGINX
docker exec nginx-lb nginx -t

# Auditoría de dependencias
pip-audit
npm audit
```

### 12.4 Control de Cambios

| Versión | Fecha | Cambios |
|---|---|---|
| 1.0 | 2026-01-15 | Documento inicial |
| 1.1 | 2026-02-01 | Sistema de sesiones únicas |
| 2.0 | 2026-02-14 | Revisión completa — seguridad de archivos (5 capas) |
| 2.1 | 2026-06-18 | **Corrección de afirmaciones incorrectas** (WAF, HTTPS, 13 permisos). Nuevas cabeceras HTTP. ClamAV efectivamente invocado. Auditoría reforzada. Actualización de dependencias. |

---

## 5. Pendientes conocidos (roadmap de seguridad)

| Ítem | Estado |
|---|---|
| HTTPS en LAN (CA interna) | Evaluado, no implementado |
| Rol de BD con privilegio mínimo por servicio | Pendiente |
| Rate limiting extendido a bulk-assign/download | Pendiente |
| Actualización mayor de `vitest` (6 vulnerabilidades dev-only) | Pendiente, requiere validación de breaking changes |
| Cookie `Secure=True` | Bloqueado hasta tener HTTPS |
| Autenticación multifactor (MFA) | Roadmap |
| Exportación de datos personales (portabilidad GDPR) | Roadmap |

---

*Documento confidencial — Clasificación: CONFIDENCIAL*
*Distribución restringida al equipo de TI y seguridad de SATC*
