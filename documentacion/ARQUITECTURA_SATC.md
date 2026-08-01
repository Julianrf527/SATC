# Arquitectura del Sistema SATC

**Sistema:** SATC (Sistema de Administración de Trámites de Corpochivor)
**Documento:** Arquitectura Técnica y Diseño del Sistema  
**Versión:** 2.1  
**Fecha:** 18 de junio de 2026  
**Autor:** Julian David Rodriguez Fernandez

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Visión General de la Arquitectura](#visión-general-de-la-arquitectura)
3. [Componentes del Sistema](#componentes-del-sistema)
4. [Escalabilidad y Alta Disponibilidad](#escalabilidad-y-alta-disponibilidad)
5. [Seguridad y Control de Acceso](#seguridad-y-control-de-acceso)
6. [Gestión de Datos y Persistencia](#gestión-de-datos-y-persistencia)
7. [Arquitectura de Red y Comunicación](#arquitectura-de-red-y-comunicación)
8. [Monitoreo y Health Checks](#monitoreo-y-health-checks)
9. [Especificaciones Técnicas](#especificaciones-técnicas)
10. [Consideraciones de Deployment](#consideraciones-de-deployment)

---

## Resumen Ejecutivo

El Sistema SATC (Sistema de Administración de Trámites de Corpochivor) es una plataforma de gestión desarrollada con arquitectura de microservicios, diseñada para soportar operaciones de trámites ambientales con alta disponibilidad, escalabilidad y seguridad.

### Características Principales

- **Arquitectura:** Microservicios con API Gateway y Reverse Proxy (Nginx)
- **Capacidad:** Optimizado para 30 usuarios simultáneos, validado hasta 100
- **Disponibilidad:** 99.9% con servicios críticos replicados
- **Tecnología:** Python/FastAPI, PostgreSQL, Redis, MinIO
- **Deployment:** Docker Compose con orquestación de 17 contenedores
- **Recursos:** 3.0 GB RAM, 4 vCPUs recomendados

### Métricas de Performance Validadas

| Métrica                    | 50 Usuarios | 75 Usuarios | 100 Usuarios |
| -------------------------- | ----------- | ----------- | ------------ |
| **Requests/segundo**       | 22.85       | 33.76       | 44.14        |
| **Tiempo respuesta (p95)** | 11ms        | 13ms        | 11ms         |
| **Failures**               | 0%          | 0%          | 0%           |
| **Requests totales**       | 6,829       | 10,045      | 13,042       |

---

## Visión General de la Arquitectura

### Diagramas del Sistema

#### Diagrama CYC (Componentes y Conectores)

![CYC SATC](assets/CYC%20SATC.jpg)

Muestra el flujo desde el browser, el Reverse Proxy (Nginx) como único punto de entrada, el API Gateway como nodo central de orquestación, los 5 microservicios especializados con sus bases de datos propias, y los servicios compartidos (Redis, MinIO, ClamAV, BackUp Service). La nomenclatura distingue conectores REST (verde), DB Connector (azul punteado), Service Connector (gris punteado) y File System Storage Driver (rojo punteado).

#### Diagrama de Despliegue (Deployment)

![DEPLOYMENT SATC](assets/DEPLOYMENT%20SATC.jpg)

Vista de infraestructura física sobre un único nodo dentro de la LAN. Muestra la separación entre red pública (Node.js + Nginx en puerto 80/8060) y red privada (contenedores guvicom con los microservicios, bases de datos y servicios compartidos). El Reverse Proxy expone el puerto 8000 al host.

#### Vista por Capas (Layered View)

![Layered View](assets/Layered%20View.jpg)

Organiza el sistema en 5 tiers:
- **Tier 5 — Edge Infrastructure:** Reverse Proxy
- **Tier 4 — Presentation:** Web Frontend (React)
- **Tier 3 — Communication:** API Gateway (FastAPI)
- **Tier 2 — Logic:** Microservicios de dominio + ClamAV + BackUp Service
- **Tier 1 — Data:** PostgreSQL ×5 + Redis + MinIO

### Patrones Arquitectónicos Implementados

1. **Reverse Proxy en el borde (Nginx)**
   - Punto de entrada único para el tráfico externo
   - Enrutamiento hacia SPA y API Gateway
   - Cabeceras HTTP de seguridad (X-Frame-Options, CSP, nosniff, Referrer-Policy)
   - Rate limiting y timeouts (sin WAF — ModSecurity fue removido)

2. **API Gateway Pattern**
   - Orquestación central de tráfico entre cliente y microservicios
   - Validación de identidad (JWT) y tokens de servicio
   - Caching y rate limiting de solicitudes

3. **Microservicios por dominio**
   - Separación clara por contexto de negocio
   - Despliegue independiente y aislamiento de fallos
   - Contratos internos estables a través del gateway

4. **Database per Service**
   - Persistencia aislada por servicio para reducir acoplamiento
   - Escalado y evolución de esquemas de forma independiente

5. **Servicios compartidos especializados**
   - Redis para sesiones y caché
   - MinIO para almacenamiento de objetos
   - ClamAV para inspección de archivos

---

## Componentes del Sistema

### Capa de borde: Reverse Proxy (Nginx)

**Responsabilidades clave:**

- Punto de entrada único para todo el tráfico externo (puerto 8000 al host).
- Enrutamiento hacia el SPA y el API Gateway.
- Cabeceras HTTP de seguridad (X-Frame-Options, CSP, nosniff, Referrer-Policy).
- Rate limiting, límites de tamaño de body (10 MB) y timeouts.

### Capa de Presentación: Frontend SPA

**Responsabilidades clave:**

- Interfaz web de usuario (React + Vite).
- Consumo de API por mismo origen (Nginx).
- Separación estricta entre UI y lógica de negocio.

### Capa de Orquestación: API Gateway

**Responsabilidades clave:**

- Validación de identidad (JWT) y tokens de servicio.
- Enrutamiento centralizado hacia microservicios.
- Normalización de políticas de cache y rate limiting.
- Observabilidad unificada de tráfico interno.

### Microservicios de Dominio

| Servicio | Dominio | Responsabilidades clave | Almacenamiento |
| --- | --- | --- | --- |
| **app-users** | Identidad y acceso | Autenticación, usuarios, roles, permisos, auditoría | PostgreSQL `user_db` + Redis sesiones |
| **app-sanctioning** | Expedientes sancionatorios | Gestión del ciclo sancionatorio, reglas de negocio | PostgreSQL `expedientes_db` |
| **app-docs** | Documentos | Versionamiento, metadatos, integración con MinIO/ClamAV | PostgreSQL `documentos_db` + MinIO |
| **app-involved** | Involucrados | Gestión de entidades relacionadas a expedientes | PostgreSQL `involucrados_db` |
| **app-infraction** | Infracciones | Catálogo y operación de infracciones | PostgreSQL `infracciones_db` |

### Servicios de Infraestructura Compartida

- **Redis:** caché y sesiones de usuario (sesión única por usuario).
- **MinIO:** almacenamiento de objetos para documentos (Files).
- **ClamAV:** análisis antivirus previo a persistencia (puerto 3310).
- **PostgreSQL por servicio:** aislamiento de datos y evolución independiente.
- **MailHog:** servicio de captura de correos para desarrollo/testing (no envía emails reales).
- **Backup service:** cronjob que respalda todas las bases de datos periódicamente.

## Arquitectura de Red y Comunicación

### Segmentación de Redes

El despliegue separa explícitamente el perímetro público de la red privada interna:

- **Red pública (`satc-public`)**: expone únicamente el reverse proxy (Nginx) y el SPA (Node.js).
- **Red privada (`satc-private`)**: contiene API Gateway, microservicios, bases de datos y servicios compartidos.

### Exposición de Superficie

- **Único punto expuesto al host:** Nginx (puerto 8000).
- **Servicios internos:** sin mapeo de puertos hacia el host; accesibles solo por DNS interno de Docker.

### Flujo de Comunicación (alto nivel)

1. **Cliente → Nginx/WAF**: todas las solicitudes entran por el reverse proxy.
2. **Nginx → API Gateway**: enrutamiento interno hacia el gateway.
3. **API Gateway → Microservicios**: orquestación y políticas centralizadas.
4. **Microservicios → Datos/Servicios compartidos**: PostgreSQL, Redis, MinIO, ClamAV.

---

## Escalabilidad y Alta Disponibilidad

### Estrategia de Replicación

#### Servicios con Alta Disponibilidad (HA)

| Servicio            | Réplicas actuales | Justificación                               |
| ------------------- | ----------------- | ------------------------------------------- |
| **api-gateway**     | 1                 | Punto único de entrada y enrutamiento       |
| **app-users**       | 1                 | Servicio de autenticación y autorización    |
| **app-sanctioning** | 1                 | Servicio principal de gestión sancionatoria |
| **app-docs**        | 1                 | Flujo documental con MinIO y antivirus      |
| **app-involved**    | 1                 | Gestión de involucrados                     |
| **app-infraction**  | 1                 | Gestión de infracciones                     |

#### Servicios Sin Réplicas

| Servicio       | Réplicas | Justificación                         |
| -------------- | -------- | ------------------------------------- |
| **PostgreSQL** | 1 c/u    | Datos aislados por dominio            |
| **Redis**      | 1        | Cache distribuido y sesiones          |
| **MinIO**      | 1        | Almacenamiento documental persistente |
| **ClamAV**     | 1        | Escaneo antivirus centralizado        |

### Capacidad de Procesamiento

#### Distribución de Workers

```
Total estimado: 16 workers concurrentes

api-gateway:     6 workers
app-users:       4 workers
app-sanctioning: 4 workers
app-docs:        1 worker
app-infraction:  1 worker
```

#### Capacidad por Usuarios Simultáneos

| Usuarios           | Workers Requeridos | Workers Disponibles | Margen aproximado |
| ------------------ | ------------------ | ------------------- | ----------------- |
| **30** (típico)    | ~5-6 workers       | 16                  | **2.7x**          |
| **50** (validado)  | ~8-10 workers      | 16                  | **1.6x**          |
| **75** (validado)  | ~12-14 workers     | 16                  | **1.1x**          |
| **100** (validado) | ~15-16 workers     | 16                  | **1.0x**          |

**Conclusión:** Sistema optimizado para 30 usuarios con capacidad validada hasta 100.

### Failover y Tolerancia a Fallos

#### Escenario 1: Fallo de API Gateway

```
Estado normal:     [GW] activo
Fallo de GW:       [X] servicio no disponible hasta reinicio
Mitigación:        restart: unless-stopped + health checks
Recuperación:      automática según política de reinicio
```

#### Escenario 2: Fallo de app-users

```
Estado normal:     [app-users] activo
Fallo de servicio: autenticación no disponible temporalmente
Mitigación:        reinicio automático y dependencia `service_healthy`
```

#### Escenario 3: Fallo de app-sanctioning

```
Estado normal:     [app-sanctioning] activo
Fallo de servicio: operaciones sancionatorias no disponibles temporalmente
Mitigación:        recuperación automática por Docker + health checks
```

### Estrategia de Escalado

#### Escalado Horizontal (Agregar Réplicas)

**Para aumentar capacidad a 150 usuarios:**

```yaml
# Duplicar servicios críticos con nuevo nombre de contenedor
# y registrar upstreams adicionales en nginx
app-users-2:
  # Copiar configuración de app-users

app-sanctioning-2:
  # Copiar configuración de app-sanctioning
```

**Resultado:**

- +8 workers (4 users + 4 sanctioning)
- Total: 24 workers (estimado)
- Capacidad: ~125-150 usuarios simultáneos

#### Escalado Vertical (Aumentar Workers)

**Modificar Dockerfile:**

```dockerfile
# Cambiar de 2 a 4 workers
CMD ["gunicorn", "main:app", "--workers", "4", ...]
```

**Impacto:**

- +100% workers por contenedor
- Requiere +50% RAM por contenedor
- Total RAM: ~4.0 GB (vs 3.0 GB actual)

---

## Arquitectura de Red y Comunicación

### Segmentación de Redes

El sistema implementa una arquitectura de dos redes isoladas para seguridad:

#### Red Pública (`satc-public`)

- **Propósito:** Punto de entrada y presentación
- **Componentes:**
  - Frontend SPA (Node.js / React, puerto interno 80)
  - Nginx Reverse Proxy (nginx:alpine, puerto interno 8060 → host 8000)
- **Exposición:** Solo el proxy en puerto 8000 del host
- **Acceso:** Disponible para usuarios en la LAN

#### Red Privada (`satc-private`)

- **Propósito:** Orquestación interna y datos
- **Componentes:**
  - API Gateway (FastAPI, orquestación)
  - Microservicios: App_Usuarios, App_Sancionatoria, App_Documentos, App_Involucrados, App_Infracciones
  - Bases de datos PostgreSQL (una por microservicio)
  - Redis (cache + sesiones)
  - MinIO (storage de archivos)
  - ClamAV (antivirus, puerto 3310)
  - MailHog (captura de emails en desarrollo)
  - BackUp Service (cronjob)
- **Acceso:** Aislada del host, solo accesible internamente
- **Conectividad bidireccional:**
  - Nginx actúa como puente: expuesto en red pública, conectado a red privada
  - Permite que el proxy enrute tráfico externo hacia servicios internos

### Topología de Despliegue

#### Mapeadores de Puertos

![MAP PORTS](assets/Mapeo%20Puertos.jpg)


#### Mapeos de Puertos Detallados

| Componente          | Red        | Puerto Int. | Puerto Ext. | Protocolo | Acceso            |
| ------------------- | ---------- | ----------- | ----------- | --------- | ----------------- |
| **Nginx-LB**        | Public     | 8060        | 8000        | HTTP      | ✓ Desde host (LAN) |
| **Frontend SPA**    | Public     | 80          | —           | HTTP      | ✓ Vía nginx       |
| **API Gateway**     | Private    | 8000        | —           | HTTP      | ✓ Vía nginx       |
| **app-users**       | Private    | 8001        | —           | HTTP      | ✓ Vía gateway     |
| **app-sanctioning** | Private    | 8002        | —           | HTTP      | ✓ Vía gateway     |
| **app-docs**        | Private    | 8003        | —           | HTTP      | ✓ Vía gateway     |
| **app-involved**    | Private    | 8004        | —           | HTTP      | ✓ Vía gateway     |
| **app-infraction**  | Private    | 8005        | —           | HTTP      | ✓ Vía gateway     |
| **PostgreSQL**      | Private    | 5432        | —           | TCP       | ✗ No expuesto    |
| **Redis**           | Private    | 6379        | —           | TCP       | ✗ No expuesto    |
| **MinIO**           | Private    | 9000/9001   | —           | HTTP      | ✗ No expuesto    |
| **ClamAV**          | Private    | 3310        | —           | TCP       | ✗ No expuesto    |
| **MailHog**         | Private    | 8025 (UI)   | —           | HTTP      | ✗ Solo desarrollo |

#### Flujo de Solicitudes

```
1. Cliente Externo
   └─> GET http://host:8000/
       └─> Nginx-LB (8000:8080)
           ├─> / (documentos estáticos)  → Frontend (80)
           └─> /api/*                   → API Gateway (8000)
               ├─> /users/*             → app-users (8001)
               ├─> /expedientes/*       → app-sanctioning (8002)
               ├─> /docs/*              → app-docs (8003)
               ├─> /involved/*          → app-involved (8004)
               └─> /infractions/*       → app-infraction (8005)
```

#### Servicios Compartidos (Red Privada)

```
Microservicios ──────────> PostgreSQL 5432 (5 instancias)
       │
       ├──────────────────> Redis 6379 (caché y sesiones)
       │
       ├──────────────────> MinIO 9000 (almacenamiento)
       │
       └──────────────────> ClamAV 3310 (antivirus)
```

### Configuración de Nginx (Reverse Proxy)

> **Nota:** ModSecurity/WAF fue removido en junio 2026. La imagen es `nginx:alpine` sin módulos adicionales.

El Nginx actúa como punto de entrada único con una responsabilidad principal: enrutamiento con cabeceras de seguridad.

```nginx
upstream frontend_backend {
    server frontend:80;
}

upstream api_gateway {
    server api-gateway:8000;
}

server {
    listen 8060;

    server_tokens off;
    client_max_body_size 10M;
    client_body_timeout 10s;
    client_header_timeout 10s;

    # Cabeceras de seguridad (junio 2026)
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'" always;

    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/m;
    limit_req zone=api_limit burst=20 nodelay;

    location / {
        proxy_pass http://frontend_backend;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /api {
        proxy_pass http://api_gateway;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_hide_header X-Powered-By;
    }
}
```

### Aislamiento de Red (Seguridad por Diseño)

#### Principios de Aislamiento

1. **No exposición de puertos internos:** Servicios en red privada no están accesibles directamente desde el host
2. **Punto de entrada único:** Todo tráfico externo pasa por Nginx + WAF
3. **Comunicación cifrada (ready):** Configuración para habilitar TLS/mTLS entre microservicios en futuro
4. **DNS interno:** Docker proporciona resolución de nombres automática (ej: `app-users:8001`)

#### Beneficios de Seguridad

- **Superficie mínima:** Solo el puerto 8000 del host expuesto, todo lo demás aislado
- **No se expone el API Gateway:** Solo accesible vía Nginx
- **Redes aisladas por función:** satc-public vs satc-private
- **Base de datos nunca expuesta:** Sin mapeo de puerto para PostgreSQL

---

## Monitoreo y Health Checks

### Health Checks de Contenedores

#### Configuración de Health Checks

**API Gateway:**

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
  interval: 10s
  timeout: 5s
  retries: 3
  start_period: 10s
```

**PostgreSQL:**

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U postgres -d user_db"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Redis:**

```yaml
healthcheck:
  test: ["CMD-SHELL", "redis-cli ping | grep PONG"]
  interval: 10s
  timeout: 3s
  retries: 3
```

**MinIO:**

```yaml
healthcheck:
  test: ["CMD-SHELL", "curl -f http://localhost:9000/minio/health/live"]
  interval: 30s
  timeout: 20s
  retries: 3
```

### Monitoreo de Recursos

#### Comando de Monitoreo en Tiempo Real

```bash
# Ver consumo de recursos de todos los contenedores
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Ejemplo de salida:
NAME                       CPU %   MEM USAGE / LIMIT     NET I/O
satc-api-gateway-1         0.24%   112MB / 384MB         1.2MB / 890KB
satc-app-users-1           3.05%   162MB / 400MB         3.4MB / 2.1MB
satc-app-sanctioning       0.22%   209MB / 256MB         890KB / 450KB
satc-postgres-users        2.89%   140MB / 200MB         1.1MB / 2.3MB
satc-clamav                0.67%   1002MB / 1400MB       120KB / 90KB
```

#### Script de Monitoreo Continuo

```powershell
# monitor_recursos.ps1
while ($true) {
    Clear-Host
    Write-Host "=== SATC System Monitor ===" -ForegroundColor Cyan
    Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n"

    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"

    Start-Sleep -Seconds 5
}
```

### Logs Centralizados

#### Configuración de Logging

**Todos los servicios usan json-file driver:**

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m" # Máximo 10 MB por archivo
    max-file: "3" # Rotar 3 archivos
```

#### Comandos de Consulta de Logs

```bash
# Ver logs en tiempo real de un servicio
docker logs -f satc-api-gateway-1

# Ver últimas 100 líneas
docker logs --tail 100 satc-app-users-1

# Filtrar por timestamp
docker logs --since 2026-02-14T10:00:00 satc-app-sanctioning

# Buscar errores en todos los gateways
docker logs satc-api-gateway-1 2>&1 | grep ERROR
docker logs satc-api-gateway-2 2>&1 | grep ERROR
docker logs satc-api-gateway-3 2>&1 | grep ERROR
```

#### Logs de Aplicación

**Formato de Log Estructurado:**

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Ejemplo de uso
logger.info(f"User {user_id} logged in successfully")
logger.error(f"Failed to connect to database: {error}")
logger.warning(f"Rate limit exceeded for IP {client_ip}")
```

---

## Especificaciones Técnicas

### Requisitos de Hardware

#### Configuración Recomendada (Producción)

**Para 30 usuarios simultáneos:**

```
CPU:  4 vCPUs (x86_64)
RAM:  3.0 GB (mínimo), 4.0 GB (recomendado)
Disk: 50 GB SSD (sistema + datos)
      + 100 GB por cada 10,000 archivos (almacenamiento MinIO)
Network: 100 Mbps (mínimo)
```

**Para 100 usuarios simultáneos:**

```
CPU:  4 vCPUs (x86_64)
RAM:  3.0 GB (validado con 2.5 GB uso real)
Disk: 50 GB SSD + almacenamiento MinIO
Network: 1 Gbps (recomendado)
```

#### Distribución de Recursos por Contenedor

| Contenedor           | CPU Límite | RAM Límite | RAM Real   | Disk (estimado)  |
| -------------------- | ---------- | ---------- | ---------- | ---------------- |
| nginx-lb             | 0.5        | 128 MB     | 21 MB      | <10 MB           |
| api-gateway-1/2/3    | 1.5        | 384 MB     | 112 MB     | <50 MB c/u       |
| app-users-1/2        | 1.0        | 400 MB     | 162 MB     | <50 MB c/u       |
| app-sanctioning-1/2  | 1.0        | 256 MB     | 209 MB     | <50 MB c/u       |
| app-docs             | 0.5        | 128 MB     | 90 MB      | <50 MB           |
| postgres-users       | 0.5        | 200 MB     | 140 MB     | 500 MB - 2 GB    |
| postgres-docs        | 0.25       | 96 MB      | 21 MB      | 100 MB - 500 MB  |
| postgres-sanctioning | 0.25       | 128 MB     | 44 MB      | 500 MB - 2 GB    |
| redis                | 0.25       | 256 MB     | 9 MB       | <100 MB          |
| minio                | 0.5        | 192 MB     | 103 MB     | Variable (datos) |
| clamav               | 1.0        | 1400 MB    | 1002 MB    | ~500 MB          |
| **TOTAL**            | **8.5**    | **4.0 GB** | **2.5 GB** | **~3-5 GB base** |

### Stack Tecnológico

#### Backend

**Lenguaje y Runtime:**

- Python 3.11
- FastAPI 0.100+ (framework web asíncrono)
- Uvicorn (ASGI server)
- Gunicorn (process manager)

**Dependencias Principales:**

```
fastapi==0.100.0
uvicorn[standard]==0.23.0
sqlalchemy==2.0.19         # ORM
asyncpg==0.28.0            # PostgreSQL driver asíncrono
python-jose[cryptography]  # JWT
passlib[bcrypt]            # Password hashing
redis==4.6.0               # Cache
boto3==1.28.0              # MinIO/S3 client
clamd==1.0.2               # ClamAV client
```

#### Frontend

**Framework:**

- React 18.2
- Vite 4.4 (build tool)
- TypeScript 5.0
- Tailwind CSS

**Librerías:**

- React Router DOM (routing)
- Axios (HTTP client)
- Zustand (state management)
- React Hook Form (forms)

#### Base de Datos

**PostgreSQL 15:**

- Driver: asyncpg (asíncrono)
- ORM: SQLAlchemy 2.0 (async mode)
- Migraciones: Alembic

#### Cache y Sesiones

**Redis 7.0:**

- Cliente: redis-py
- Serialización: JSON
- TTL configurable por tipo de dato

#### Storage

**MinIO (Latest):**

- API compatible con AWS S3
- Cliente: boto3
- Bucket principal: `satc-documentos`

#### Orquestación

**Docker Compose 2.20+:**

- Networks: bridge
- Volumes: named volumes
- Health checks: nativos
- Dependencies: service_healthy condition

---

## Consideraciones de Deployment

### Variables de Entorno

#### Archivo .env (Template)

```bash
# ====================================
# SATC - Variables de Entorno
# ====================================

# Secrets (cambiar en producción)
SECRET_KEY=<your-secret-key-256-bits>
SECRET_KEY_GATEWAY=<gateway-secret-key>
SECRET_GATEWAY=<gateway-shared-secret>

# PostgreSQL
POSTGRES_PASSWORD=<strong-password>

# Redis
REDIS_PASSWORD=<redis-password>

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=<strong-password>

# SMTP (para notificaciones)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<email@example.com>
SMTP_PASSWORD=<app-password>
SMTP_FROM=noreply@satc.com

# Configuración de seguridad
MAX_FILE_SIZE_MB=10
CLAMAV_ENABLED=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# CORS (dominios permitidos)
CORS_ORIGINS=http://localhost:5173,http://localhost:80

# Cache
CACHE_TYPE=redis
CACHE_TTL=900  # 15 minutos

# Timezone
TZ=America/Bogota
```

### Comandos de Despliegue

#### Primera Instalación

```bash
# 1. Clonar repositorio
git clone https://github.com/your-org/satc.git
cd satc

# 2. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar valores de producción

# 3. Inicializar bases de datos (opcional)
cd db-script
./apply_all_migrations.ps1

# 4. Construir y levantar servicios
docker-compose build
docker-compose up -d

# 5. Verificar health de servicios
docker ps --format "table {{.Names}}\t{{.Status}}"

# 6. Ver logs iniciales
docker-compose logs -f --tail=100
```

#### Actualización de Servicios

```bash
# 1. Detener servicios sin pérdida de datos
docker-compose down

# 2. Actualizar código
git pull origin main

# 3. Reconstruir imágenes
docker-compose build --no-cache

# 4. Levantar con nuevas versiones
docker-compose up -d

# 5. Verificar logs de errores
docker-compose logs --since 5m | grep ERROR
```

#### Rollback en Caso de Fallo

```bash
# 1. Detener servicios actuales
docker-compose down

# 2. Volver a versión anterior
git checkout <previous-commit-hash>

# 3. Restaurar imágenes
docker-compose build
docker-compose up -d

# 4. Verificar funcionamiento
curl http://localhost:80/health
```

### Estrategia de Migración de Datos

#### Migraciones de Base de Datos con Alembic

```bash
# Estructura de carpetas
app-users/migrations/
  ├── alembic.ini
  ├── env.py
  └── versions/
      ├── 001_initial_schema.py
      ├── 002_add_user_roles.py
      └── 003_add_permissions.py
```

**Ejecutar Migraciones:**

```bash
# Dentro del contenedor
docker exec -it satc-app-users-1 bash
alembic upgrade head

# O con script automatizado
docker exec satc-app-users-1 python -m alembic upgrade head
```

**Rollback de Migración:**

```bash
docker exec satc-app-users-1 python -m alembic downgrade -1
```

### Troubleshooting Común

#### Problema: Contenedor no levanta (unhealthy)

**Diagnóstico:**

```bash
# Ver logs completos
docker logs satc-app-users-1

# Ver health check específico
docker inspect satc-app-users-1 | grep -A 10 Health

# Verificar conectividad a dependencias
docker exec satc-app-users-1 nc -zv postgres-users 5432
```

**Soluciones:**

1. Verificar variables de entorno (DATABASE_URL)
2. Confirmar que bases de datos están healthy
3. Revisar permisos de volúmenes
4. Reiniciar contenedor: `docker restart satc-app-users-1`

#### Problema: Alta latencia en respuestas

**Diagnóstico:**

```bash
# Ver uso de CPU/RAM
docker stats satc-api-gateway-1

# Revisar logs de performance
docker logs satc-api-gateway-1 | grep "took.*ms"
```

**Soluciones:**

1. Verificar cache de Redis está funcionando
2. Revisar queries lentas en PostgreSQL
3. Aumentar workers si CPU < 50%
4. Agregar réplica adicional

#### Problema: Base de datos llena

**Diagnóstico:**

```bash
# Ver tamaño de volúmenes
docker system df -v

# Revisar tamaño de tablas
docker exec satc-postgres-users psql -U postgres -d user_db -c "
  SELECT tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
  FROM pg_tables WHERE schemaname = 'public';
"
```

**Soluciones:**

1. Purgar logs antiguos
2. Vacuumar base de datos: `VACUUM FULL`
3. Archivar datos históricos
4. Expandir volumen de disco

---

## Conclusiones y Recomendaciones

### Fortalezas de la Arquitectura Actual

✅ **Alta Disponibilidad:** Recuperación automática con health checks y políticas de reinicio  
✅ **Rendimiento Validado:** 0% failures con 100 usuarios simultáneos  
✅ **Eficiencia de Recursos:** 2.5 GB RAM real vs 3.0 GB configurados (83%)  
✅ **Seguridad Robusta:** JWT + RBAC + Antivirus + Deduplicación  
✅ **Escalabilidad Horizontal:** Fácil agregar réplicas según demanda  
✅ **Separación de Concerns:** Microservicios independientes

---

## Referencias y Documentación Adicional

### Enlaces Externos

**Tecnologías:**

- FastAPI: https://fastapi.tiangolo.com/
- Docker Compose: https://docs.docker.com/compose/
- PostgreSQL: https://www.postgresql.org/docs/
- Redis: https://redis.io/documentation
- MinIO: https://min.io/docs/minio/linux/index.html
- ClamAV: https://docs.clamav.net/

**Mejores Prácticas:**

- Microservices Patterns: https://microservices.io/
- 12 Factor App: https://12factor.net/
- Docker Best Practices: https://docs.docker.com/develop/dev-best-practices/

---

**Fin del Documento**

_Última actualización: 18 de junio de 2026_  
_Versión: 2.1_  
_Clasificación: Documentación Técnica Interna_
