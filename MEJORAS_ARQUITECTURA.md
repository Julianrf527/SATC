# Mejoras y Correcciones Arquitectónicas - Sistema ApiCorp

> Documento de trabajo para mejoras conceptuales y técnicas previo al despliegue en producción.  
> **Fecha:** Enero 2026  
> **Estado:** En planificación

---

## 📋 Índice de Casos

### 🔴 CRÍTICOS (Resolver antes de despliegue)

| # | Caso | Estado |
|---|------|--------|
| 15 | [Estrategia de Datos Primarios (Seeds)](#caso-15-estrategia-de-datos-primarios-seeds) | ⏳ Pendiente |
| 11 | [Disaster Recovery (RTO/RPO)](#caso-11-disaster-recovery-rtorpo) | ⏳ Pendiente |
| 13 | [Invalidación Inmediata de Tokens](#caso-13-invalidación-inmediata-de-tokens) | ⏳ Pendiente |
| 8 | [Seguridad en Subida de Archivos](#caso-8-seguridad-en-subida-de-archivos) | ⏳ Pendiente |
| 1 | [Manejo de Fallos en Comunicación Inter-Servicio](#caso-1-manejo-de-fallos-en-comunicación-inter-servicio) | ⏳ Pendiente |
| 4 | [Caché Distribuido](#caso-4-caché-distribuido) | ⏳ Pendiente |
| 3 | [Alta Disponibilidad de app-users](#caso-3-alta-disponibilidad-de-app-users) | ⏳ Pendiente |

### 🟡 IMPORTANTES (Resolver pronto)

| # | Caso | Estado |
|---|------|--------|
| 2 | [Sesión Única por Usuario](#caso-2-sesión-única-por-usuario) | ⏳ Pendiente |
| 7 | [Validación de Tamaño de Archivos](#caso-7-validación-de-tamaño-de-archivos) | ⏳ Pendiente |
| 12 | [Rate Limiting (Protección DoS)](#caso-12-rate-limiting-protección-dos) | ⏳ Pendiente |
| 5 | [Circuit Breaker Real](#caso-5-circuit-breaker-real) | ⏳ Pendiente |
| 9 | [Auditoría Sistemática](#caso-9-auditoría-sistemática) | ⏳ Pendiente |
| 10 | [Manejo Consistente de Timezone](#caso-10-manejo-consistente-de-timezone) | ⏳ Pendiente |
| 16 | [Observabilidad y Trazabilidad](#caso-16-observabilidad-y-trazabilidad) | ⏳ Pendiente |

### 🟢 OPCIONALES (Futuro)

| # | Caso | Estado |
|---|------|--------|
| 6 | [Versionado de API](#caso-6-versionado-de-api) | ⏳ Pendiente |
| 14 | [Deduplicación de Archivos](#caso-14-deduplicación-de-archivos) | ⏳ Pendiente |

---

## CASO 1: Manejo de Fallos en Comunicación Inter-Servicio

### 🎯 Problema
Cuando un microservicio llama a otro (vía Gateway) y falla la comunicación, el sistema no tiene una estrategia clara de qué hacer.

### 📊 Escenario Real
```
1. app-sancionatoria crea expediente → OK ✅
2. Intenta notificar a app-users → FALLA ❌ (timeout, servicio reiniciándose, etc.)
3. ¿Qué hacer?
   a) ¿Rollback del expediente?
   b) ¿Guardar sin notificar?
   c) ¿Reintentar N veces?
   d) ¿Encolar para procesar después?
```

### 💡 Solución Propuesta

**Opción A: Reintentos con Fallback (Recomendado para red local)**
```python
# Conceptual - No implementado aún
from tenacity import retry, stop_after_attempt, wait_fixed

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
async def call_user_service(url, data):
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        if response.status_code >= 500:
            raise httpx.HTTPError("Servicio no disponible")
        return response
```

**Estrategia:**
1. Intentar enviar notificación 3 veces (con 2s entre intentos)
2. Si falla → Loguear error pero continuar con el expediente
3. Admin puede ver notificaciones fallidas en panel
4. Opción manual de reenviar

**Ventajas:**
- ✅ No bloquea operación principal
- ✅ Simple de implementar
- ✅ Apropiado para red local (fallos esporádicos)

**Desventajas:**
- ❌ Notificación puede perderse definitivamente
- ❌ No garantiza entrega

### 📝 Tareas
- [ ] Implementar librería `tenacity` para reintentos
- [ ] Definir cuáles operaciones son críticas vs opcionales
- [ ] Crear tabla `notificaciones_fallidas` para tracking
- [ ] Endpoint admin para ver y reenviar notificaciones fallidas

### 🔗 Archivos Afectados
- `app-sancionatoria/routes/*`
- `app-docs/routes/*`
- Cualquier lugar que llame a `httpx.AsyncClient`

---

## CASO 2: Sesión Única por Usuario

### 🎯 Problema
Un usuario puede tener múltiples sesiones activas simultáneamente desde diferentes equipos/navegadores.

### 📊 Escenario Real
```
Usuario Juan:
- Login desde PC oficina → Token A (válido 24h)
- Login desde laptop casa → Token B (válido 24h)
- Login desde celular → Token C (válido 24h)

Todos los tokens válidos simultáneamente
```

### 💡 Solución Propuesta

**Estrategia: Sesión única con invalidación automática**

1. **Agregar tabla de sesiones activas:**
```sql
CREATE TABLE sesiones_activas (
    id SERIAL PRIMARY KEY,
    usuario_id INT REFERENCES usuarios(id),
    token_jti VARCHAR(255) UNIQUE,  -- JWT ID único
    ip_address VARCHAR(50),
    user_agent TEXT,
    fecha_login TIMESTAMP,
    fecha_ultimo_uso TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE
);
```

2. **Al login:**
   - Invalidar todas las sesiones anteriores del usuario
   - Crear nueva sesión
   - Devolver token con `jti` único

3. **Al validar token:**
   - Verificar que `jti` existe y está activo en DB
   - Actualizar `fecha_ultimo_uso`

**Ventajas:**
- ✅ Control total de sesiones
- ✅ Puede invalidar inmediatamente
- ✅ Puede ver sesiones activas por usuario

**Desventajas:**
- ❌ Requiere consulta DB en cada request (caché ayuda)
- ❌ Ya no es JWT stateless puro

### 📝 Tareas
- [ ] Crear migración para tabla `sesiones_activas`
- [ ] Modificar `/auth/login` para invalidar sesiones anteriores
- [ ] Modificar `verify_gateway_token` para validar `jti` en DB
- [ ] Endpoint admin para ver sesiones activas de un usuario
- [ ] Endpoint usuario para cerrar sesiones remotas

### 🔗 Archivos Afectados
- `app-users/routes/auth.py`
- `app-users/db/models/` (nuevo modelo)
- `api-gateway/utils/checkToken.py`

---

## CASO 3: Alta Disponibilidad de app-users

### 🎯 Problema
**app-users** es un **Single Point of Failure (SPOF)**. Si cae, todo el sistema deja de funcionar:
- No se puede autenticar
- No se puede validar permisos
- No se pueden enviar notificaciones

### 📊 Observación
Tienes razón: si un expediente se crea, queda vinculado al `creador_id` directamente en la DB, así que esa parte está cubierta. El problema es si cae **durante** la operación.

### 💡 Solución Propuesta

**Opción A: Réplicas de app-users (Docker)**
```yaml
# docker-compose.yml
services:
  app-users:
    image: apicorp-users
    deploy:
      replicas: 3  # 3 instancias
    networks:
      - apicorp-network
      
  app-users-loadbalancer:
    image: nginx:alpine
    volumes:
      - ./nginx-lb.conf:/etc/nginx/nginx.conf
    depends_on:
      - app-users
```

**Opción B: Healthcheck + Auto-restart**
```yaml
app-users:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
    interval: 10s
    timeout: 5s
    retries: 3
  restart: unless-stopped
```

**Para red local (recomendado):**
- Opción B es suficiente (auto-restart)
- Monitoreo simple de salud
- Backup manual de la instancia

### 📝 Tareas
- [ ] Crear endpoint `/health` en todos los servicios
- [ ] Configurar healthchecks en docker-compose
- [ ] Configurar restart policies
- [ ] Documentar procedimiento de recuperación manual

### 🔗 Archivos Afectados
- `app-users/main.py` (agregar endpoint health)
- `docker-compose.yml`

---

## CASO 4: Caché Distribuido

### 🎯 Problema
El caché de tokens en el API Gateway es **local en memoria**:
```python
TOKEN_CACHE = {}  # Solo en este contenedor
```

Si tienes múltiples instancias del Gateway (para alta disponibilidad), cada una tiene su propio caché → inconsistencia.

### 📊 Escenario Real
```
Gateway-1: Usuario autentica → Cache almacena token
Gateway-2: Mismo usuario hace request → Cache vacío, debe decodificar JWT nuevamente
```

### 💡 Solución Propuesta

**Opción A: Redis (Recomendado si escalas)**
```python
import redis.asyncio as redis

redis_client = redis.Redis(
    host='redis',
    port=6379,
    decode_responses=True
)

async def get_cached_token(token: str):
    return await redis_client.get(f"token:{token}")

async def cache_token(token: str, data: dict, ttl: int = 120):
    await redis_client.setex(f"token:{token}", ttl, json.dumps(data))
```

**Opción B: Sin caché (Simple, para red local)**
- Eliminar caché completamente
- Siempre decodificar JWT (es rápido)
- Simplifica arquitectura

**Para red local con baja concurrencia:**
- **Opción B recomendada** (sin caché)
- JWT decode es muy rápido (~0.1ms)
- Menos complejidad

### 📝 Tareas
- [ ] Decidir: ¿Redis o sin caché?
- [ ] Si Redis: Agregar servicio en docker-compose
- [ ] Si sin caché: Eliminar `TOKEN_CACHE` del Gateway
- [ ] Benchmark: medir diferencia con/sin caché

### 🔗 Archivos Afectados
- `api-gateway/main.py`
- `docker-compose.yml` (si se agrega Redis)

---

## CASO 5: Circuit Breaker Real

### 🎯 Problema
Tienes variables declaradas pero **no implementadas**:
```python
CIRCUIT_BREAKER = {}
CIRCUIT_BREAKER_THRESHOLD = 5
CIRCUIT_BREAKER_TIMEOUT = 30
```

### 📊 ¿Qué es Circuit Breaker?

**Patrón de diseño** para evitar llamadas a servicios que están fallando:

```
Estado CERRADO (normal):
├─ Llamada → Servicio → Responde OK ✅

Estado ABIERTO (fallando):
├─ Detecta 5 fallos consecutivos
├─ Deja de intentar por 30 segundos
└─ Devuelve error inmediato (sin llamar)

Estado SEMI-ABIERTO:
├─ Después de 30s, intenta 1 llamada de prueba
├─ Si funciona → Vuelve a CERRADO
└─ Si falla → Vuelve a ABIERTO
```

**Beneficio:** Evita saturar un servicio que ya está caído, permitiéndole recuperarse.

### 💡 Solución Propuesta

**Usar librería existente:**
```python
from pybreaker import CircuitBreaker

# Configuración por servicio
breakers = {
    "users": CircuitBreaker(
        fail_max=5,           # Fallos antes de abrir
        timeout_duration=30   # Segundos abierto
    ),
    "sanctioning": CircuitBreaker(fail_max=5, timeout_duration=30),
    "documents": CircuitBreaker(fail_max=5, timeout_duration=30),
}

# Al hacer llamada
try:
    response = await breakers["users"].call(
        http_client.get, f"{MICROSERVICES['users']}/endpoint"
    )
except CircuitBreakerError:
    raise HTTPException(503, "Servicio temporalmente no disponible")
```

### 📝 Tareas
- [ ] Instalar librería `pybreaker`
- [ ] Implementar circuit breakers en Gateway
- [ ] Configurar thresholds apropiados
- [ ] Agregar endpoint para ver estado de breakers
- [ ] Logging cuando se abre/cierra un breaker

### 🔗 Archivos Afectados
- `api-gateway/main.py`
- `requirements.txt`

---

## CASO 6: Versionado de API

### 🎯 Problema
Sin versionado, cambios en el backend pueden romper el frontend.

### 📊 Escenario Real
```
Backend actual devuelve:
{
  "nombre": "Juan",
  "correo": "juan@example.com"
}

Frontend espera: response.nombre ✅

Backend nuevo devuelve:
{
  "nombre_completo": "Juan Pérez",
  "email": "juan@example.com"
}

Frontend: response.nombre → undefined ❌
💥 Frontend se rompe
```

### 💡 Solución Propuesta

**Estrategia: Backward Compatibility (Mantener compatibilidad)**

En lugar de versionado complejo, **mantener campos antiguos**:
```python
# Backend nuevo
return {
    "nombre": user.nombre,           # ✅ Campo antiguo (mantener)
    "nombre_completo": user.nombre,  # ✅ Campo nuevo
    "correo": user.correo,           # ✅ Campo antiguo (mantener)
    "email": user.correo             # ✅ Campo nuevo (alias)
}
```

**Regla:** Nunca eliminar campos, solo agregar nuevos.

**Para red local:** Esto es suficiente. Versionado `/api/v1/`, `/api/v2/` es para APIs públicas con múltiples clientes.

### 📝 Tareas
- [ ] Documentar regla: "No eliminar campos en responses"
- [ ] Si es necesario cambiar estructura, agregar campos nuevos
- [ ] Deprecar campos antiguos gradualmente (documentar como @deprecated)
- [ ] Frontend migra a nuevos campos con tiempo

### 🔗 Archivos Afectados
- Todos los endpoints que devuelven JSON
- Documentación de API

---

## CASO 7: Validación de Tamaño de Archivos

### 🎯 Problema
Mencionas que hay límite de 10MB, pero debe estar **validado explícitamente** en el backend.

### 📊 Problema Conceptual
Aunque el frontend valide, alguien puede hacer request directo con `curl` o Postman y subir archivos gigantes.

### 💡 Solución Propuesta

**Implementar en cada endpoint de upload:**

```python
from fastapi import UploadFile, HTTPException

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@app.post("/document/upload")
async def upload_document(file: UploadFile):
    # Leer en chunks para no cargar todo en memoria
    total_size = 0
    chunks = []
    
    while chunk := await file.read(8192):  # 8KB chunks
        total_size += len(chunk)
        if total_size > MAX_FILE_SIZE:
            raise HTTPException(413, "Archivo excede el límite de 10MB")
        chunks.append(chunk)
    
    # Procesar archivo...
    content = b''.join(chunks)
```

**Adicional: Configurar Nginx**
```nginx
# nginx.conf
client_max_body_size 10M;
```

### 📝 Tareas
- [ ] Agregar validación en `app-sancionatoria/routes/document.py`
- [ ] Agregar validación en `app-docs/routes/docs.py`
- [ ] Configurar `client_max_body_size` en Nginx
- [ ] Variable de entorno `MAX_FILE_SIZE_MB` configurable
- [ ] Tests con archivos >10MB

### 🔗 Archivos Afectados
- `app-sancionatoria/routes/document.py`
- `app-docs/routes/docs.py`
- `frontend/nginx.conf`

---

## CASO 8: Seguridad en Subida de Archivos

### 🎯 Problema
Al permitir subida de archivos, el sistema está expuesto a múltiples vectores de ataque:
- **Malware/Virus** - Archivos ejecutables maliciosos
- **Scripts maliciosos** - JavaScript, PHP embebidos en documentos
- **Path Traversal** - Nombres como `../../etc/passwd`
- **Zip Bombs** - Archivos comprimidos que explotan al descomprimirse
- **XXE/XSS** - Payloads en XML/SVG
- **Archivos disfrazados** - Ejecutables renombrados como .pdf

### 📊 Escenario Real
```
Usuario sube: "contrato.pdf"
Archivo real: script.exe renombrado
Sistema guarda sin validar
Otro usuario descarga
Windows ejecuta automáticamente
💥 Infección en red local
```

### 💡 Solución Propuesta

**Capa 1: Validación de Extensión**
```python
ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
    '.txt', '.jpg', '.jpeg', '.png'
}

DANGEROUS_EXTENSIONS = {
    '.exe', '.bat', '.cmd', '.com', '.pif', '.scr',
    '.vbs', '.js', '.jar', '.ps1', '.sh', '.dll'
}

def validate_extension(filename: str):
    ext = os.path.splitext(filename)[1].lower()
    
    if ext in DANGEROUS_EXTENSIONS:
        raise HTTPException(400, "Tipo de archivo no permitido")
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Extensión {ext} no permitida")
```

**Capa 2: Validación por Magic Bytes (MIME Real)**
```python
import magic

async def validate_file_type(file: UploadFile):
    # Leer primeros bytes para detectar tipo real
    header = await file.read(2048)
    await file.seek(0)  # Resetear posición
    
    # Detectar tipo real del archivo
    mime = magic.from_buffer(header, mime=True)
    
    ALLOWED_MIMES = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'image/jpeg',
        'image/png',
        'text/plain'
    }
    
    if mime not in ALLOWED_MIMES:
        raise HTTPException(
            400, 
            f"Tipo de archivo no permitido. Detectado: {mime}"
        )
    
    # Verificar que extensión coincida con MIME
    ext = os.path.splitext(file.filename)[1].lower()
    
    MIME_TO_EXT = {
        'application/pdf': ['.pdf'],
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        # ...
    }
    
    if ext not in MIME_TO_EXT.get(mime, []):
        raise HTTPException(
            400,
            "Extensión no coincide con el contenido del archivo"
        )
```

**Capa 3: Sanitización de Nombre de Archivo**
```python
import re
import unicodedata

def sanitize_filename(filename: str) -> str:
    # Eliminar caracteres especiales
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.encode('ascii', 'ignore').decode('ascii')
    
    # Eliminar path traversal
    filename = os.path.basename(filename)
    filename = filename.replace('..', '')
    
    # Solo caracteres permitidos
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    
    # Longitud máxima
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    
    # Generar nombre único con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{name}{ext}"
```

**Capa 4: Escaneo Antivirus (Opcional pero Recomendado)**
```python
import clamd

async def scan_for_malware(file_path: str):
    """Escanear archivo con ClamAV"""
    try:
        cd = clamd.ClamdUnixSocket()
        result = cd.scan(file_path)
        
        if result and result[file_path][0] == 'FOUND':
            virus_name = result[file_path][1]
            # Eliminar archivo inmediatamente
            os.remove(file_path)
            raise HTTPException(
                400, 
                f"Archivo infectado detectado: {virus_name}"
            )
    except Exception as e:
        # Log error pero no bloquear si antivirus no disponible
        logger.warning(f"No se pudo escanear archivo: {e}")
```

**Capa 5: Aislamiento de Archivos**
```python
# Guardar archivos fuera del directorio web
UPLOAD_DIR = "/var/apicorp/secure-uploads"  # Fuera de webroot

# Servir archivos a través de endpoint controlado (no acceso directo)
@app.get("/documents/download/{file_id}")
async def download_file(file_id: int, request: Request):
    # Verificar permisos del usuario
    user_id = verify_gateway_token(request)
    
    # Obtener metadata del archivo
    file_meta = await get_file_metadata(file_id)
    
    # Verificar que usuario tiene permiso
    if not await user_can_access_file(user_id, file_meta):
        raise HTTPException(403, "Sin permisos")
    
    # Servir archivo con headers de seguridad
    return FileResponse(
        file_meta.path,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename={file_meta.nombre}",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'"
        }
    )
```

**Implementación Completa en Endpoint:**
```python
@router.post("/document/upload")
async def upload_document(
    file: UploadFile,
    documento_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    # 1. Validar tamaño
    if file.size > MAX_FILE_SIZE:
        raise HTTPException(413, "Archivo muy grande")
    
    # 2. Validar extensión
    validate_extension(file.filename)
    
    # 3. Validar MIME type real
    await validate_file_type(file)
    
    # 4. Sanitizar nombre
    safe_filename = sanitize_filename(file.filename)
    
    # 5. Guardar temporalmente
    temp_path = f"/tmp/{safe_filename}"
    content = await file.read()
    async with aiofiles.open(temp_path, 'wb') as f:
        await f.write(content)
    
    # 6. Escanear virus (si disponible)
    await scan_for_malware(temp_path)
    
    # 7. Mover a ubicación final segura
    final_path = f"{UPLOAD_DIR}/{documento_id}/{safe_filename}"
    os.makedirs(os.path.dirname(final_path), exist_ok=True)
    shutil.move(temp_path, final_path)
    
    # 8. Guardar metadata en DB
    await db.execute(
        """
        INSERT INTO archivos (documento_id, nombre_original, nombre_guardado, 
                             mime_type, tamaño, ruta)
        VALUES (:doc_id, :original, :saved, :mime, :size, :path)
        """,
        {
            "doc_id": documento_id,
            "original": file.filename,
            "saved": safe_filename,
            "mime": file.content_type,
            "size": file.size,
            "path": final_path
        }
    )
    
    return {"ok": True, "filename": safe_filename}
```

### 📝 Tareas
- [ ] Instalar librería `python-magic` para detección MIME
- [ ] Implementar validación de extensiones
- [ ] Implementar validación de magic bytes
- [ ] Sanitización de nombres de archivo
- [ ] Mover uploads fuera de webroot
- [ ] Endpoints de descarga con verificación de permisos
- [ ] Headers de seguridad en respuestas de archivos
- [ ] (Opcional) Instalar y configurar ClamAV para escaneo
- [ ] Docker: Servicio ClamAV en docker-compose
- [ ] Logging de intentos de subida de archivos sospechosos
- [ ] Alertas admin cuando se detecta archivo malicioso

### 🔗 Archivos Afectados
- `app-sancionatoria/routes/document.py`
- `app-docs/routes/docs.py`
- `app-*/utils/file_security.py` (crear)
- `requirements.txt` (agregar python-magic, clamd)
- `docker-compose.yml` (agregar ClamAV opcional)

### ⚠️ Consideraciones Adicionales

**Para red local:**
- Si tienes antivirus corporativo en los clientes, ClamAV puede ser opcional
- Pero las validaciones de extensión y MIME son **obligatorias**
- Path traversal y sanitización son **críticos**

**Configuración ClamAV (opcional):**
```yaml
# docker-compose.yml
services:
  clamav:
    image: clamav/clamav:latest
    container_name: apicorp-clamav
    volumes:
      - clamav-data:/var/lib/clamav
    networks:
      - apicorp-network
    healthcheck:
      test: ["CMD", "clamdscan", "--ping"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  clamav-data:
```

---

## CASO 9: Auditoría Sistemática

### 🎯 Problema
Actualmente hay auditoría parcial, pero no sistemática. Dificulta responder:
- ¿Quién vio el expediente X?
- ¿Quién modificó el campo Y?
- ¿Desde qué IP se accedió?

### 💡 Solución Propuesta

**Crear tabla centralizada de auditoría:**

```sql
CREATE TABLE auditoria_sistema (
    id SERIAL PRIMARY KEY,
    fecha TIMESTAMP DEFAULT NOW(),
    usuario_id INT,
    usuario_nombre VARCHAR(255),
    accion VARCHAR(50),        -- CREATE, READ, UPDATE, DELETE
    recurso VARCHAR(50),       -- expediente, documento, usuario
    recurso_id VARCHAR(100),   -- ID del recurso afectado
    endpoint VARCHAR(255),     -- /sanctioning/file/create
    metodo VARCHAR(10),        -- POST, GET, PUT, DELETE
    ip_address VARCHAR(50),
    cambios JSONB,             -- {"campo": {"antes": "X", "despues": "Y"}}
    metadata JSONB             -- Info adicional
);

CREATE INDEX idx_auditoria_usuario ON auditoria_sistema(usuario_id);
CREATE INDEX idx_auditoria_recurso ON auditoria_sistema(recurso, recurso_id);
CREATE INDEX idx_auditoria_fecha ON auditoria_sistema(fecha DESC);
```

**Middleware de auditoría automática:**
```python
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    user_id = request.headers.get("X-Gateway-User-Id")
    
    response = await call_next(request)
    
    # Loguear si es operación importante
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        await log_audit(
            usuario_id=user_id,
            accion=request.method,
            endpoint=request.url.path,
            ip=request.client.host
        )
    
    return response
```

### 📝 Tareas
- [ ] Crear tabla `auditoria_sistema` en cada DB o centralizada
- [ ] Crear modelo SQLAlchemy
- [ ] Implementar middleware de auditoría
- [ ] Endpoint admin para consultar logs
- [ ] Filtros: por usuario, fecha, recurso
- [ ] Retención: eliminar logs >1 año automáticamente

### 🔗 Archivos Afectados
- `app-users/db/models/` (nuevo modelo)
- Todos los `main.py` (middleware)
- Nuevo módulo `utils/audit.py`

---

## CASO 10: Manejo Consistente de Timezone

### 🎯 Problema
El sistema debe funcionar **siempre en hora colombiana** (America/Bogota) por temas legales.

### 📊 Observación
Tienes razón, no es negociable. Pero el **concepto** es: ¿Cómo garantizas que TODO el sistema use la misma zona?

### 💡 Solución Propuesta

**1. Configurar timezone en Docker:**
```dockerfile
# Dockerfile de cada servicio
ENV TZ=America/Bogota
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
```

**2. Configurar timezone en Python:**
```python
# Cada main.py
import os
import pytz

TIMEZONE = pytz.timezone('America/Bogota')
os.environ['TZ'] = 'America/Bogota'

# Al obtener fecha actual
from datetime import datetime
def now_colombia():
    return datetime.now(TIMEZONE)
```

**3. PostgreSQL timezone:**
```sql
-- Configurar en DB
SET TIME ZONE 'America/Bogota';
```

**4. Frontend consistente:**
```typescript
// Siempre formatear en zona Colombia
const formatDate = (date: string) => {
  return new Date(date).toLocaleString('es-CO', {
    timeZone: 'America/Bogota'
  });
};
```

### 📝 Tareas
- [ ] Agregar `ENV TZ=America/Bogota` en todos los Dockerfiles
- [ ] Crear helper `now_colombia()` en utils
- [ ] Reemplazar todos los `datetime.now()` por `now_colombia()`
- [ ] Configurar PostgreSQL timezone
- [ ] Frontend: formatear fechas consistentemente
- [ ] Tests de timezone

### 🔗 Archivos Afectados
- Todos los Dockerfiles
- `app-*/utils/` (helpers de fecha)
- `frontend/src/utils/dateFormat.ts`

---

## CASO 11: Disaster Recovery (RTO/RPO)

### 🎯 Problema
**Preguntas críticas sin respuesta:**
1. Si el servidor se quema, ¿cuánto tardas en recuperar? **(RTO)**
2. ¿Cuántos datos puedes perder? **(RPO)**
3. ¿Dónde están los backups?
4. ¿Cada cuánto se hacen?

### 📊 Definiciones

**RTO (Recovery Time Objective):** Tiempo máximo de downtime aceptable
- Ejemplo: 4 horas

**RPO (Recovery Point Objective):** Pérdida de datos aceptable
- Ejemplo: Backup cada 6 horas → Puedes perder máximo 6h de datos

### 💡 Solución Propuesta

**1. Definir RTO y RPO según negocio:**

```
Propuesta para red local:
├─ RTO: 4 horas (media jornada laboral)
├─ RPO: 24 horas (backup diario nocturno)
└─ Justificación: Procesos administrativos no son tiempo real
```

**2. Estrategia de Backup:**

```yaml
# Ya descrito en conversación anterior
Backups automáticos:
├─ DB: Diario a las 2 AM (pg_dump)
├─ Archivos: Incremental cada hora + completo semanal
├─ Retención: 30 días diarios, 4 semanas, 6 meses
└─ Ubicación: Disco externo / NAS / Servidor backup
```

**3. Plan de Recuperación:**

```bash
# Documentar procedimiento
1. Levantar servidor nuevo
2. Instalar Docker
3. Restaurar código desde Git
4. Restaurar DB desde último backup
5. Restaurar archivos desde backup
6. Levantar docker-compose
7. Validar funcionamiento
Tiempo estimado: 2-3 horas
```

### 📝 Tareas
- [ ] Definir RTO/RPO con stakeholders
- [ ] Implementar backups automáticos (ya discutido)
- [ ] Documentar procedimiento de recuperación paso a paso
- [ ] Probar recuperación completa (simulacro)
- [ ] Definir ubicación de backups off-site
- [ ] Responsables de cada paso

### 🔗 Archivos Afectados
- `scripts/backup-db.sh`
- `scripts/backup-files.sh`
- `scripts/restore.sh`
- `docs/DISASTER_RECOVERY.md` (crear)

---

## CASO 12: Rate Limiting (Protección DoS)

### 🎯 Problema
Sin rate limiting, alguien (malicioso o accidental) puede saturar el sistema.

### 📊 Observación
Correcto: el objetivo es **proteger el sistema**, no distinguir por rol.

### 💡 Solución Propuesta

**Opción A: Rate Limiting en API Gateway (Recomendado)**

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Límite global
@app.middleware("http")
@limiter.limit("100/minute")  # 100 requests por minuto por IP
async def global_rate_limit(request: Request, call_next):
    return await call_next(request)

# Límite específico en endpoints sensibles
@app.post("/auth/login")
@limiter.limit("5/minute")  # Solo 5 intentos de login por minuto
async def login(...):
    ...
```

**Configuración sugerida:**
```
Límites globales (por IP):
├─ General: 100 req/min
├─ Login: 5 intentos/min
├─ Upload: 10 archivos/hora
└─ Búsquedas: 50 req/min
```

**Opción B: Rate Limiting en Nginx (más eficiente)**
```nginx
http {
    limit_req_zone $binary_remote_addr zone=general:10m rate=100r/m;
    limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
    
    server {
        location / {
            limit_req zone=general burst=20;
        }
        
        location /auth/login {
            limit_req zone=login burst=3;
        }
    }
}
```

### 📝 Tareas
- [ ] Decidir: Python (slowapi) o Nginx
- [ ] Instalar y configurar rate limiting
- [ ] Definir límites apropiados por endpoint
- [ ] Respuesta HTTP 429 con mensaje claro
- [ ] Logging de rate limit violations
- [ ] Whitelist para IPs internas si es necesario

### 🔗 Archivos Afectados
- `api-gateway/main.py` (si slowapi)
- `nginx.conf` (si Nginx)
- `requirements.txt`

---

## CASO 13: Invalidación Inmediata de Tokens

### 🎯 Problema
JWT stateless: Una vez emitido, válido hasta `exp`, **incluso si desactivas al usuario**.

### 📊 Escenario Crítico
```
1. Usuario Juan tiene token válido 24h
2. Admin lo desactiva a las 10 AM
3. Juan sigue accediendo hasta las 10 AM del día siguiente
💥 Riesgo de seguridad
```

### 💡 Solución Propuesta

**Estrategia: Validación en cada request**

Ya lo tienes parcialmente implementado en el Gateway, pero falta validar **estado del usuario**.

**Flujo actual:**
```
Gateway → Decodifica JWT → Extrae user_id → Inyecta en header
Microservicio → NO valida si usuario está activo
```

**Flujo necesario:**
```
Gateway → Decodifica JWT → Extrae user_id → 
  → Consulta app-users: ¿Usuario activo? →
    → Si activo: Continúa
    → Si inactivo: HTTP 401
```

**Implementación:**

```python
# api-gateway/main.py
async def validate_user_active(user_id: int) -> bool:
    try:
        response = await http_client.get(
            f"{MICROSERVICES['users']}/user/status/{user_id}",
            timeout=2.0
        )
        return response.json().get("activo", False)
    except:
        return False  # Si no puede validar, denegar acceso

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def gateway(request: Request, path: str):
    # ... decode JWT ...
    
    # Validar usuario activo (con caché)
    if not await validate_user_active(user_id):
        raise HTTPException(401, "Usuario inactivo")
    
    # ... continuar ...
```

**Con caché (optimización):**
```python
# Cachear por 30 segundos (balance entre seguridad y performance)
@cached(ttl=30)
async def validate_user_active(user_id: int) -> bool:
    ...
```

### 📝 Tareas
- [ ] Crear endpoint `/user/status/{id}` en app-users (solo retorna si activo)
- [ ] Modificar Gateway para validar usuario en cada request
- [ ] Implementar caché corto (30s) para no saturar DB
- [ ] Endpoint público (sin auth) para el Gateway
- [ ] Tests: desactivar usuario y verificar que token deja de funcionar

### 🔗 Archivos Afectados
- `api-gateway/main.py`
- `app-users/routes/user.py` (nuevo endpoint)

---

## CASO 14: Deduplicación de Archivos

### 🎯 Problema
Mismo archivo subido múltiples veces ocupa espacio innecesario.

### 📊 Escenario
```
Usuario A sube: politicas_2025.pdf (5 MB)
Usuario B sube: politicas_2025.pdf (5 MB, mismo archivo)
Sistema almacena: 10 MB (duplicado)
```

### 💡 Solución Propuesta

**Estrategia: Hash-based storage**

```python
import hashlib

async def save_file_deduplicated(file: UploadFile):
    # Leer contenido
    content = await file.read()
    
    # Calcular hash (identificador único del contenido)
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Ruta basada en hash
    file_path = f"uploads/storage/{file_hash[:2]}/{file_hash}.bin"
    
    # Si ya existe, no guardar
    if not os.path.exists(file_path):
        # Guardar archivo
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
    
    # Guardar metadata en DB
    await db.execute(
        """
        INSERT INTO archivos_metadata 
        (hash, nombre_original, mime_type, tamaño, documento_id)
        VALUES (:hash, :nombre, :mime, :size, :doc_id)
        """,
        {
            "hash": file_hash,
            "nombre": file.filename,
            "mime": file.content_type,
            "size": len(content),
            "doc_id": documento_id
        }
    )
    
    return file_hash
```

**Estructura:**
```
uploads/
  storage/  # Archivos únicos por hash
    ab/
      abc123def456... .bin
    cd/
      cde456fgh789....bin
  
  metadata en DB:
    hash -> nombre_original, documento_id, referencias
```

**Ventajas:**
- ✅ Ahorro significativo de espacio
- ✅ Backup más eficiente
- ✅ Evita corrupción (hash valida integridad)

**Desventajas:**
- ❌ Más complejidad
- ❌ No puedes eliminar archivo si múltiples documentos lo referencian

### 📝 Tareas
- [ ] Crear tabla `archivos_metadata` con hash, nombre, referencias
- [ ] Implementar función de guardado con hash
- [ ] Migrar archivos existentes (script)
- [ ] Lógica de eliminación: verificar referencias antes de borrar
- [ ] Endpoint para ver duplicados y espacio ahorrado

### 🔗 Archivos Afectados
- `app-sancionatoria/routes/document.py`
- `app-docs/routes/docs.py`
- `app-*/db/models/` (nueva tabla)
- `scripts/migrate-files-to-hash.py` (crear)

---

## CASO 15: Estrategia de Datos Primarios (Seeds)

### 🎯 Problema
Al desplegar por primera vez, la DB está vacía. ¿Cómo se crean?
- Roles base (admin, operador, revisor)
- Permisos
- Usuario administrador default
- Etapas de expedientes
- Configuraciones del sistema

### 💡 Solución Propuesta

**Script de inicialización idempotente:**

```python
# scripts/seed_database.py
import asyncio
from sqlalchemy import select
from app_users.db.database import AsyncSessionLocal
from app_users.db.models.role import Role
from app_users.db.models.permiso import Permiso
from app_users.db.models.usuario import Usuario

async def seed_roles():
    async with AsyncSessionLocal() as db:
        # Verificar si ya existen
        result = await db.execute(select(Role).where(Role.name == "Administrador"))
        if result.scalar_one_or_none():
            print("✅ Roles ya existen, saltando...")
            return
        
        # Crear roles
        roles = [
            Role(name="Administrador", description="Acceso total"),
            Role(name="Operador", description="Gestión expedientes"),
            Role(name="Revisor", description="Revisión documentos"),
        ]
        db.add_all(roles)
        await db.commit()
        print("✅ Roles creados")

async def seed_permisos():
    async with AsyncSessionLocal() as db:
        # Verificar si ya existen
        result = await db.execute(select(Permiso).limit(1))
        if result.scalar_one_or_none():
            print("✅ Permisos ya existen, saltando...")
            return
        
        # Crear permisos base
        permisos = [
            Permiso(name="usuarios", path="/users/*"),
            Permiso(name="expedientes", path="/sanctioning/*"),
            Permiso(name="documentos", path="/documents/*"),
            # ... más permisos
        ]
        db.add_all(permisos)
        await db.commit()
        print("✅ Permisos creados")

async def seed_admin_user():
    async with AsyncSessionLocal() as db:
        # Verificar si ya existe admin
        result = await db.execute(
            select(Usuario).where(Usuario.correo == "admin@sistema.local")
        )
        if result.scalar_one_or_none():
            print("✅ Usuario admin ya existe, saltando...")
            return
        
        # Obtener rol admin
        admin_role = await db.execute(select(Role).where(Role.name == "Administrador"))
        admin_role = admin_role.scalar_one()
        
        # Crear usuario admin
        from app_users.utils.passwords import hash_password
        admin = Usuario(
            nombre="Administrador",
            correo="admin@sistema.local",
            contraseña=hash_password("Admin@2026"),  # Cambiar en producción
            rol_id=admin_role.id,
            activo=True
        )
        db.add(admin)
        await db.commit()
        print("✅ Usuario admin creado")
        print("   Email: admin@sistema.local")
        print("   Password: Admin@2026")

async def main():
    print("🌱 Iniciando seed de base de datos...")
    await seed_roles()
    await seed_permisos()
    # Asignar permisos a roles...
    await seed_admin_user()
    print("✅ Seed completado")

if __name__ == "__main__":
    asyncio.run(main())
```

**Ejecutar automáticamente en Docker:**
```dockerfile
# Dockerfile
CMD ["sh", "-c", "python scripts/seed_database.py && uvicorn main:app --host 0.0.0.0"]
```

O manualmente tras despliegue:
```bash
docker exec apicorp-users python scripts/seed_database.py
```

### 📝 Tareas
- [ ] Crear `scripts/seed_database.py` para cada servicio
- [ ] Definir roles, permisos, usuario admin base
- [ ] Etapas de expedientes (app-sancionatoria)
- [ ] Estados de documentos (app-docs)
- [ ] Script idempotente (no duplicar si ya existe)
- [ ] Documentar credenciales default
- [ ] Procedimiento para cambiar password admin tras instalación

### 🔗 Archivos Afectados
- `scripts/seed_database.py` (crear en cada app)
- `Dockerfile` (cada servicio)
- `docs/INSTALACION.md` (documentar)

---

## CASO 16: Observabilidad y Trazabilidad

### 🎯 Problema
Cuando un request toma mucho tiempo o falla, es difícil saber dónde está el problema:
- ¿El Gateway?
- ¿El microservicio?
- ¿Una query SQL?
- ¿Una llamada a otro servicio?

### 💡 Solución Propuesta

**Nivel 1: Logging Estructurado (Básico)**

```python
import logging
import json
import time

logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Request ID único para trazabilidad
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    logger.info(json.dumps({
        "event": "request_start",
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "user_id": request.headers.get("X-Gateway-User-Id")
    }))
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    logger.info(json.dumps({
        "event": "request_end",
        "request_id": request_id,
        "duration_ms": round(duration * 1000, 2),
        "status_code": response.status_code
    }))
    
    return response
```

**Nivel 2: Métricas Básicas (Opcional)**

```python
from prometheus_client import Counter, Histogram

# Métricas
request_count = Counter('http_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'Request duration', ['endpoint'])

@app.get("/metrics")
async def metrics():
    from prometheus_client import generate_latest
    return Response(generate_latest(), media_type="text/plain")
```

**Nivel 3: Distributed Tracing (Avanzado - Futuro)**
- OpenTelemetry + Jaeger
- Trace ID que sigue el request por todos los servicios
- Visualización de cuellos de botella

### 📝 Tareas
- [ ] Implementar logging estructurado (JSON) en todos los servicios
- [ ] Request ID único que se propaga entre servicios
- [ ] Logging de tiempos de respuesta
- [ ] (Opcional) Endpoint `/metrics` con Prometheus
- [ ] (Futuro) Evaluar OpenTelemetry si se necesita más detalle

### 🔗 Archivos Afectados
- Todos los `main.py` (middleware de logging)
- `utils/logging.py` (helpers)
- `requirements.txt` (prometheus-client si se usa)

---

## 📊 Resumen de Prioridades

### 🔴 **CRÍTICOS (Resolver antes de despliegue):**
- [ ] **Caso 1:** Manejo de fallos inter-servicio (reintentos)
- [ ] **Caso 3:** Alta disponibilidad app-users (healthcheck + restart)
- [ ] **Caso 4:** Caché distribuido o eliminar caché
- [ ] **Caso 8:** Seguridad en subida de archivos (validación + sanitización)
- [ ] **Caso 11:** Disaster Recovery (backups automáticos)
- [ ] **Caso 13:** Invalidación inmediata de tokens
- [ ] **Caso 15:** Seeds de datos primarios

### 🟡 **IMPORTANTES (Resolver pronto):**
- [ ] **Caso 2:** Sesión única por usuario
- [ ] **Caso 5:** Circuit breaker real
- [ ] **Caso 7:** Validación tamaño archivos
- [ ] **Caso 9:** Auditoría sistemática
- [ ] **Caso 10:** Timezone consistente
- [ ] **Caso 12:** Rate limiting DoS
- [ ] **Caso 16:** Observabilidad básica

### 🟢 **OPCIONALES (Futuro):**
- [ ] **Caso 6:** Versionado API (solo si es necesario)
- [ ] **Caso 14:** Deduplicación archivos

---

## 📝 Notas Finales

- **Este documento debe actualizarse** a medida que se completan tareas
- Cada caso debe tener issue/ticket en sistema de gestión
- Priorizar según impacto en negocio y complejidad técnica
- Coordinar con stakeholders para casos críticos (RTO/RPO, sesión única, etc.)

**Próximo paso:** Revisar con equipo y comenzar por casos CRÍTICOS.

---

**Última actualización:** Enero 8, 2026  
**Estado:** En planificación  
**Responsable:** Equipo de desarrollo ApiCorp
