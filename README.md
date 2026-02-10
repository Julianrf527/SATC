# ApiCorp - Sistema de Gestión Corporativa

> Sistema empresarial modular para gestión de expedientes sancionatorios, control documental con versionamiento y administración centralizada de usuarios bajo arquitectura de microservicios.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19.1-61DAFB.svg)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)

---

## 📚 Tabla de Contenidos

### [1. Arquitectura](#1-arquitectura)
- [1.1 Visión General](#11-visión-general)
- [1.2 Microservicios](#12-microservicios)
- [1.3 Comunicación](#13-comunicación-entre-servicios)

### [2. Seguridad](#2-seguridad)
- [2.1 Sistema JWT](#21-sistema-jwt-dual-key)
- [2.2 Flujo de Autenticación](#22-flujo-de-autenticación)
- [2.3 Control de Permisos](#23-control-de-permisos)

### [3. Base de Datos](#3-base-de-datos)
- [3.1 Arquitectura](#31-arquitectura-de-datos)
- [3.2 Esquemas](#32-esquemas-por-microservicio)
- [3.3 Optimizaciones](#33-optimizaciones)

### [4. Flujos de Negocio](#4-flujos-de-negocio)
- [4.1 Gestión Documental](#41-gestión-documental)
- [4.2 Expedientes Sancionatorios](#42-expedientes-sancionatorios)

### [5. Implementación](#5-implementación)
- [5.1 Stack Tecnológico](#51-stack-tecnológico)
- [5.2 Instalación](#52-instalación)
- [5.3 Configuración](#53-configuración)
- [5.4 Despliegue](#54-despliegue)

---

## 1. Arquitectura

### 1.1 Visión General

ApiCorp implementa una arquitectura de microservicios desacoplados que se comunican a través de un API Gateway centralizado, siguiendo el patrón Database-per-Service para aislamiento de datos.

```mermaid
flowchart TB
    %% CAPA DE PRESENTACIÓN
    subgraph Cliente["CAPA DE PRESENTACIÓN"]
        WEB["Cliente Web<br/>React + TypeScript<br/>Puerto: 5173"]
    end

    %% CAPA DE GATEWAY
    subgraph Gateway["CAPA DE GATEWAY"]
        GW["API Gateway<br/>FastAPI + httpx<br/>Puerto: 8000"]
    end

    %% CAPA DE SERVICIOS
    subgraph Microservicios["CAPA DE SERVICIOS"]
        USERS["app-users<br/>FastAPI<br/>Puerto: 8002"]
        SANC["app-sancionatoria<br/>FastAPI<br/>Puerto: 8001"]
        DOCS["app-docs<br/>FastAPI<br/>Puerto: 8003"]
    end

    %% CAPA DE PERSISTENCIA
    subgraph Persistencia["CAPA DE PERSISTENCIA"]
        DB1[("user_db<br/>PostgreSQL 15")]
        DB2[("sancionatoria_db<br/>PostgreSQL 15")]
        DB3[("documentos_db<br/>PostgreSQL 15")]
    end

    %% FLUJO PRINCIPAL
    WEB -->|HTTP/REST<br/>JWT Cookie| GW

    GW -->|REST<br/>/users/*| USERS
    GW -->|REST<br/>/sancionatoria/*| SANC
    GW -->|REST<br/>/docs/*| DOCS

    %% COMUNICACIÓN ENTRE SERVICIOS VÍA GATEWAY
    SANC -.->|REST consume<br/>/users/*| GW
    DOCS -.->|REST consume<br/>/users/*| GW

    %% PERSISTENCIA
    USERS -->|SQLAlchemy<br/>Pool| DB1
    SANC -->|SQLAlchemy<br/>Pool| DB2
    DOCS -->|SQLAlchemy<br/>Pool| DB3

    %% ESTILOS
    style WEB fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    style GW fill:#fff9c4,stroke:#f57f17,stroke-width:3px

    style USERS fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style SANC fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    style DOCS fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px

    style DB1 fill:#ffccbc,stroke:#bf360c,stroke-width:2px
    style DB2 fill:#ffccbc,stroke:#bf360c,stroke-width:2px
    style DB3 fill:#ffccbc,stroke:#bf360c,stroke-width:2px
```

**Principios de Diseño:**
- **Separación de Responsabilidades**: Cada microservicio gestiona su dominio de negocio
- **Database per Service**: Cada servicio posee su propia base de datos aislada
- **API Gateway Pattern**: Punto único de entrada, autenticación y enrutamiento
- **Service-to-Service**: Comunicación REST a través del Gateway con tokens internos
- **Comunicación Asíncrona**: httpx AsyncClient con HTTP/2 y connection pooling
- **Escalabilidad Horizontal**: Servicios stateless, fácil replicación y balanceo
- **Desacoplamiento**: Sin dependencias directas entre bases de datos de servicios

**Leyenda de Conectores:**
- **Líneas sólidas (→)**: Comunicación HTTP/REST directa
- **Líneas punteadas (⋯→)**: Comunicación inter-servicio vía Gateway
- **X-Gateway-***: Headers personalizados (User-Id, Token, Permissions)

**Nota de Implementación:** 
> Aunque en el entorno actual las 3 bases de datos PostgreSQL están en el mismo servidor (localhost), la arquitectura está diseñada para permitir la distribución de cada base de datos en servidores independientes sin modificar el código de los microservicios. Cada servicio solo conoce su propia cadena de conexión.

---

### 1.2 Microservicios

#### app-users (Puerto 8002)
**Dominio:** Identidad, Acceso y Comunicaciones

```
┌─────────────────────────────────────────┐
│           app-users (8002)              │
├─────────────────────────────────────────┤
│ Responsabilidades:                      │
│ • Autenticación (Login/Logout)          │
│ • Gestión de usuarios (CRUD)            │
│ • Roles y permisos (RBAC)               │
│ • Notificaciones en sistema             │
│ • Envío de emails (SMTP)                │
│ • Auditoría de acciones                 │
│ • Recuperación de contraseñas           │
├─────────────────────────────────────────┤
│ Endpoints Clave:                        │
│ POST   /auth/login                      │
│ POST   /auth/register                   │
│ GET    /auth/me                         │
│ POST   /auth/logout                     │
│ GET    /user/list                       │
│ PATCH  /user/toggle-state/{id}          │
│ GET    /role/list                       │
│ POST   /notification/create             │
│ POST   /email/send                      │
└─────────────────────────────────────────┘
```

**Base de Datos:** `user_db`

---

#### app-sancionatoria (Puerto 8001)
**Dominio:** Expedientes y Procesos Legales

```
┌─────────────────────────────────────────┐
│      app-sancionatoria (8001)           │
├─────────────────────────────────────────┤
│ Responsabilidades:                      │
│ • Gestión de expedientes                │
│ • Control de involucrados               │
│ • Documentos de expediente              │
│ • Flujo de etapas procesales            │
│ • Actos administrativos                 │
│ • Sistema de alertas automáticas        │
│ • Gestión geográfica                    │
├─────────────────────────────────────────┤
│ Endpoints Clave:                        │
│ GET    /file/list                       │
│ POST   /file/create                     │
│ PATCH  /file/encargado/{id}             │
│ GET    /involved/manage                 │
│ PUT    /involved/manage/{id}            │
│ POST   /document/upload                 │
│ GET    /town/municipalities             │
└─────────────────────────────────────────┘
```

**Base de Datos:** `sancionatoria_db`

---

#### app-docs (Puerto 8003)
**Dominio:** Control Documental y Versionamiento

```
┌─────────────────────────────────────────┐
│          app-docs (8003)                │
├─────────────────────────────────────────┤
│ Responsabilidades:                      │
│ • Gestión de documentos corporativos    │
│ • Control de versiones automático       │
│ • Flujo de revisión multi-revisor       │
│ • Aprobación/Devolución documentos      │
│ • Auditoría de cambios                  │
│ • Notificaciones de workflow            │
│ • Gestión de revisores                  │
├─────────────────────────────────────────┤
│ Endpoints Clave:                        │
│ GET    /docs/list                       │
│ POST   /docs/create                     │
│ GET    /docs/detail/{id}                │
│ POST   /docs/upload-version/{id}        │
│ POST   /docs/review/{id}                │
│ GET    /docs/stats                      │
│ GET    /docs/reviewers                  │
└─────────────────────────────────────────┘
```

**Base de Datos:** `documentos_db`

**Estados del Documento:**
```
en_revision → aprobado → finalizado
            ↘ rechazado → (nueva versión) → en_revision
```

---

#### api-gateway (Puerto 8000)
**Dominio:** Enrutamiento y Seguridad

```
┌─────────────────────────────────────────┐
│         api-gateway (8000)              │
├─────────────────────────────────────────┤
│ Responsabilidades:                      │
│ • Proxy reverso a microservicios        │
│ • Decodificación y validación JWT       │
│ • Inyección de headers de contexto      │
│ • Caché de tokens (LRU, TTL: 120s)      │
│ • Circuit breaker (5 fallos, 30s)       │
│ • Compresión GZip                       │
│ • Enrutamiento basado en prefijo        │
├─────────────────────────────────────────┤
│ Configuración:                          │
│ • Cache Size: 500 tokens                │
│ • Cache TTL: 120 segundos               │
│ • Circuit Threshold: 5 fallos           │
│ • Circuit Timeout: 30 segundos          │
│ • HTTP Client: httpx AsyncClient        │
│ • Compression: GZip                     │
└─────────────────────────────────────────┘
```

---

### 1.3 Comunicación entre Servicios

#### Patrón de Comunicación

```
┌─────────────────────────────────────────────────────────────┐
│              FLUJO DE REQUEST/RESPONSE                       │
└─────────────────────────────────────────────────────────────┘

Cliente → Gateway
┌────────────────────────────────┐
│ Cookie: access_token=<JWT>     │
│ Content-Type: application/json │
│ Accept: application/json       │
└────────────────────────────────┘

Gateway → Microservicio
┌─────────────────────────────────────────────────────┐
│ X-Gateway-Token: validated_token                    │
│ X-Gateway-User-Id: 123                              │
│ X-Gateway-Permissions: ["perm_1", "perm_2", ...]    │
│ Content-Type: application/json                      │
└─────────────────────────────────────────────────────┘

Microservicio ↔ Microservicio (via Gateway)
┌────────────────────────────────────────────────────┐
│ X-Service-Token: internal_jwt                      │
│ Gateway-URL: http://localhost:8000                 │
└────────────────────────────────────────────────────┘
```

#### Mapeo de Rutas

| Prefijo | Destino | Puerto |
|---------|---------|--------|
| `/users/*` | app-users | 8002 |
| `/sanctioning/*` | app-sancionatoria | 8001 |
| `/documents/*` | app-docs | 8003 |

**Rutas Públicas** (sin autenticación):
- `auth/login`
- `auth/register`
- `auth/recovery-code`
- `auth/recovery`

**Rutas sin Caché**:
- `auth/logout`
- `user/delete`
- `admin/*`

---

## 2. Seguridad

### 2.1 Sistema JWT Dual-Key

ApiCorp implementa un sistema de seguridad con dos niveles de claves secretas:

```
┌──────────────────────────────────────────────────────────┐
│                 DUAL SECRET KEY SYSTEM                    │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  SECRET_KEY 🔒                                           │
│  ├─ Alcance: Privada de cada microservicio              │
│  ├─ Uso: Tokens internos, operaciones locales           │
│  ├─ Ubicación: .env de cada servicio                    │
│  └─ Generación: openssl rand -hex 32                    │
│                                                           │
│  SECRET_KEY_GATEWAY 🔑                                   │
│  ├─ Alcance: Compartida (api-gateway ↔ app-users)       │
│  ├─ Uso: JWT de autenticación principal                 │
│  ├─ Ubicación: .env de gateway y app-users              │
│  └─ Requisito: DEBE SER IDÉNTICA en ambos servicios     │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**Ventajas del Modelo Dual:**
- ✅ Aislamiento de seguridad entre servicios
- ✅ Tokens de autenticación validados solo por gateway
- ✅ Reducción de superficie de ataque
- ✅ Flexibilidad para rotación de keys

---

### 2.2 Flujo de Autenticación

```mermaid
sequenceDiagram
    participant C as Cliente
    participant G as Gateway
    participant U as app-users
    participant S as app-sancionatoria

    Note over C,S: FASE 1 - LOGIN
    C->>G: POST /auth/login {user, password}
    G->>U: Proxy request
    U->>U: Validar credenciales (bcrypt)
    U->>U: Query permisos FROM roles
    U->>U: JWT encode con SECRET_KEY_GATEWAY
    U->>G: Set-Cookie access_token=JWT
    G->>C: 200 OK + Cookie

    Note over C,S: FASE 2 - REQUEST AUTENTICADO
    C->>G: GET /sanctioning/file/list + Cookie
    G->>G: JWT decode con SECRET_KEY_GATEWAY
    G->>G: Extract user_id y permissions
    G->>S: Headers X-Gateway-User-Id + Permissions
    S->>S: verify_permission(required_perm)
    S->>S: Process business logic
    S->>G: Response data
    G->>C: Response data

    Note over C,S: FASE 3 - LOGOUT
    C->>G: POST /auth/logout
    G->>U: Proxy request
    U->>U: Invalidar sesión
    U->>G: Clear-Cookie access_token
    G->>C: 200 OK
```

**Diagrama de Flujo Detallado:**

```
┌─────────────┐
│   LOGIN     │
└──────┬──────┘
       │
       ├─► 1. Usuario envía credenciales
       │
       ├─► 2. app-users valida (bcrypt)
       │   └─ SELECT * FROM usuarios WHERE correo = ?
       │
       ├─► 3. Query permisos del rol
       │   └─ SELECT p.name FROM roles_permisos
       │      JOIN permisos p ON ...
       │
       ├─► 4. Generar JWT
       │   └─ Payload: {
       │       "sub": user_id,
       │       "permissions": ["perm_1", "perm_2", ...],
       │       "exp": now() + 24h
       │      }
       │   └─ Firma: SECRET_KEY_GATEWAY
       │
       └─► 5. Set Cookie httpOnly
           └─ access_token=<JWT>

┌──────────────────┐
│  REQUEST A API   │
└────────┬─────────┘
         │
         ├─► 6. Gateway extrae Cookie
         │
         ├─► 7. Decodificar JWT
         │   └─ jwt.decode(token, SECRET_KEY_GATEWAY)
         │   └─ Resultado: {user_id: 123, permissions: [...]}
         │
         ├─► 8. Inyectar Headers
         │   └─ X-Gateway-Token: validated_token
         │   └─ X-Gateway-User-Id: 123
         │   └─ X-Gateway-Permissions: JSON([...])
         │
         ├─► 9. Microservicio valida en memoria
         │   └─ verify_permission(request, "required_perm")
         │   └─ if "required_perm" in permissions: OK
         │      else: HTTP 403
         │
         └─► 10. Procesar lógica de negocio
             └─ SIN consultas a DB para auth
```

---

### 2.3 Control de Permisos

#### Modelo de Permisos

```
┌──────────────────────────────────────────────────────┐
│              ESTRUCTURA RBAC                         │
├──────────────────────────────────────────────────────┤
│                                                       │
│  Usuario                                              │
│  ├─ id: 123                                          │
│  ├─ correo: "user@corp.com"                         │
│  ├─ rol_id: 2                                        │
│  └─ permisos: ["perm_1", "perm_2", "perm_3"]  ◄─┐   │
│                                                  │   │
│  Rol                                             │   │
│  ├─ id: 2                                        │   │
│  ├─ nombre: "Revisor"                            │   │
│  └─ permisos: ─────────────────────────────────────┘   │
│      ├─ "documento_revisar"                          │
│      ├─ "expediente_ver"                             │
│      └─ "notificacion_recibir"                       │
│                                                       │
│  Permiso                                              │
│  ├─ id: 5                                            │
│  ├─ nombre: "documento_revisar"                      │
│  ├─ path: "/documents/review"                        │
│  └─ descripcion: "Revisar documentos asignados"      │
│                                                       │
└──────────────────────────────────────────────────────┘
```

#### Verificación Zero-DB-Query

```python
# En Microservicio (app-sancionatoria/routes/involved.py)

from utils.verify_gateway_token import verify_permission

@router.get("/manage")
async def manage_involved(request: Request):
    # Validación de permiso SIN consultar base de datos
    user_id = verify_permission(request, "expediente_gestionar involucrados")
    
    # user_id ya está validado, continuar con lógica de negocio
    # ...
```

**Proceso Interno de verify_permission:**
```
1. Extraer header X-Gateway-Permissions
   └─ JSON.parse → ["perm_1", "perm_2", "perm_3"]

2. Verificar si permiso requerido está en lista
   └─ "expediente_gestionar involucrados" in permissions?

3. Si SÍ: retornar user_id
   Si NO: raise HTTPException(403, "No tienes permiso")

Tiempo de ejecución: ~0.1ms (solo operaciones en memoria)
```

**Comparación con Modelo Tradicional:**

| Aspecto | Modelo JWT (ApiCorp) | Modelo DB Query |
|---------|---------------------|-----------------|
| Latencia | ~0.1ms | ~5-50ms |
| Carga DB | 0 queries/request | 1+ queries/request |
| Escalabilidad | Alta (stateless) | Limitada (DB bottleneck) |
| Actualización | Re-login | Tiempo real |
| Seguridad | Alta (firmado) | Alta (centralizado) |

---

## 3. Base de Datos

### 3.1 Arquitectura de Datos

**Estrategia:** Database per Service Pattern

```
┌──────────────────────────────────────────────────────────┐
│         PostgreSQL 15 Server (localhost:5432)            │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │  user_db   │  │sancionatoria_db │  │documentos_db │  │
│  ├────────────┤  ├─────────────────┤  ├──────────────┤  │
│  │ 7 tablas   │  │ 15 tablas       │  │ 6 tablas     │  │
│  │ ~50 MB     │  │ ~200 MB         │  │ ~100 MB      │  │
│  └────────────┘  └─────────────────┘  └──────────────┘  │
│                                                           │
│  Owner:          Owner:              Owner:              │
│  app-users       app-sancionatoria   app-docs            │
│                                                           │
└──────────────────────────────────────────────────────────┘

Ventajas:
✓ Aislamiento de datos
✓ Esquemas independientes
✓ Escalado independiente
✓ Backups granulares
✓ Sin dependencias cruzadas
```

---

### 3.2 Esquemas por Microservicio

#### user_db

```sql
-- Autenticación e Identidad
┌───────────────────────────────────────────────┐
│ usuarios                                      │
├───────────────────────────────────────────────┤
│ id (PK, SERIAL)                               │
│ cedula (UNIQUE, BIGINT)                       │
│ primer_nombre, segundo_nombre (VARCHAR)       │
│ primer_apellido, segundo_apellido (VARCHAR)   │
│ correo (UNIQUE, VARCHAR)                      │
│ contraseña (VARCHAR - bcrypt hash)            │
│ rol_id (FK → roles.id)                        │
│ state (BOOLEAN - activo/inactivo)             │
│ fecha_creacion (TIMESTAMP)                    │
└───────────────────────────────────────────────┘

-- RBAC
┌─────────────────┐  ┌──────────────────┐  ┌───────────────────┐
│ roles           │  │ permisos         │  │ roles_permisos    │
├─────────────────┤  ├──────────────────┤  ├───────────────────┤
│ id (PK)         │  │ id (PK)          │  │ rol_id (FK)       │
│ name (UNIQUE)   │  │ name (UNIQUE)    │  │ permiso_id (FK)   │
│ descripcion     │  │ path             │  │ (PK compuesta)    │
└─────────────────┘  │ descripcion      │  └───────────────────┘
                      └──────────────────┘

-- Notificaciones
┌───────────────────────────────────────────────┐
│ notificaciones                                │
├───────────────────────────────────────────────┤
│ id (PK, SERIAL)                               │
│ usuario_id (FK → usuarios.id)                 │
│ mensaje (TEXT)                                │
│ tipo (VARCHAR - expediente, documento, etc)   │
│ leida (BOOLEAN, DEFAULT false)                │
│ id_vinculada (VARCHAR - radicado/doc_id)      │
│ fecha_creacion (TIMESTAMP)                    │
└───────────────────────────────────────────────┘

-- Auditoría
┌───────────────────────────────────────────────┐
│ auditoria                                     │
├───────────────────────────────────────────────┤
│ id (PK, BIGSERIAL)                            │
│ usuario_id (FK → usuarios.id)                 │
│ accion (VARCHAR - crear, editar, eliminar)   │
│ tabla (VARCHAR)                               │
│ datos_anteriores (JSON)                       │
│ datos_nuevos (JSON)                           │
│ fecha (TIMESTAMP)                             │
└───────────────────────────────────────────────┘
```

---

#### sancionatoria_db

```sql
-- Expedientes
┌───────────────────────────────────────────────┐
│ expedientes                                   │
├───────────────────────────────────────────────┤
│ radicado (PK, VARCHAR - formato: EXP-YYYYMMDD-NNNN) │
│ nombre (VARCHAR)                              │
│ descripcion (TEXT)                            │
│ etapa_id (FK → etapas.id)                     │
│ encargado_id (INT - ref externa user_db)      │
│ estado (VARCHAR - activo, cerrado, archivado) │
│ fecha_creacion (TIMESTAMP)                    │
└───────────────────────────────────────────────┘

-- Involucrados
┌───────────────────────────────────────────────┐
│ involucrados                                  │
├───────────────────────────────────────────────┤
│ id (PK, SERIAL)                               │
│ numero_documento (BIGINT)                     │
│ tipo_documento (VARCHAR - CC, CE, NIT, etc)   │
│ digito_verificacion (VARCHAR, NULLABLE)       │
│ nombre (VARCHAR)                              │
│ celular (BIGINT)                              │
│ correo (VARCHAR)                              │
│ UNIQUE(numero_documento, tipo_documento)      │
└───────────────────────────────────────────────┘

-- Relación Expediente-Involucrado
┌───────────────────────────────────────────────┐
│ involucrado_expediente                        │
├───────────────────────────────────────────────┤
│ id (PK, SERIAL)                               │
│ expediente_radicado (FK → expedientes)        │
│ involucrado_id (FK → involucrados.id)         │
│ rol (VARCHAR - demandante, demandado, etc)    │
│ observaciones (TEXT)                          │
│ UNIQUE(expediente_radicado, involucrado_id)   │
└───────────────────────────────────────────────┘

-- Etapas Procesales
┌───────────────────────────────────────────────┐
│ etapas                                        │
├───────────────────────────────────────────────┤
│ id (PK, SERIAL)                               │
│ nombre (VARCHAR - Formulación, Decisión, etc) │
│ descripcion (TEXT)                            │
│ orden (INT)                                   │
└───────────────────────────────────────────────┘

-- Geografía
┌───────────────────────┐  ┌──────────────────────┐
│ municipios            │  │ veredas              │
├───────────────────────┤  ├──────────────────────┤
│ codigo (PK, VARCHAR)  │  │ id (PK, SERIAL)      │
│ nombre (VARCHAR)      │  │ nombre (VARCHAR)     │
│ departamento (VARCHAR)│  │ municipio_codigo (FK)│
└───────────────────────┘  └──────────────────────┘
```

---

#### documentos_db

```sql
-- Control Documental
┌───────────────────────────────────────────────┐
│ documentos                                    │
├───────────────────────────────────────────────┤
│ id (PK, SERIAL)                               │
│ nombre (VARCHAR)                              │
│ descripcion (TEXT)                            │
│ tipo_archivo (VARCHAR - pdf, docx, xlsx)     │
│ usuario_creador_id (INT - ref user_db)        │
│ estado (VARCHAR - en_revision, aprobado,      │
│         rechazado, finalizado)                │
│ version_actual (INT, DEFAULT 1)               │
│ numero_devoluciones (INT, DEFAULT 0)          │
│ fecha_creacion (TIMESTAMP)                    │
│ fecha_ultima_actualizacion (TIMESTAMP)        │
└───────────────────────────────────────────────┘

-- Versionamiento
┌───────────────────────────────────────────────┐
│ versiones_documento                           │
├───────────────────────────────────────────────┤
│ id (PK, SERIAL)                               │
│ documento_id (FK → documentos.id, CASCADE)    │
│ numero_version (INT)                          │
│ archivo_url (VARCHAR - path relativo)         │
│ archivo_nombre_original (VARCHAR)             │
│ archivo_size (BIGINT - bytes)                 │
│ usuario_subida_id (INT - ref user_db)         │
│ comentario (TEXT)                             │
│ fecha_subida (TIMESTAMP)                      │
│ UNIQUE(documento_id, numero_version)          │
└───────────────────────────────────────────────┘

-- Flujo de Revisión
┌───────────────────────────────────────────────┐
│ revisiones                                    │
├───────────────────────────────────────────────┤
│ id (PK, SERIAL)                               │
│ documento_id (FK → documentos.id)             │
│ revisor_id (INT - ref user_db)                │
│ version_revisada (INT)                        │
│ estado_revision (VARCHAR - aprobado, devuelto)│
│ comentarios (TEXT)                            │
│ fecha_revision (TIMESTAMP)                    │
└───────────────────────────────────────────────┘

┌───────────────────────────────────────────────┐
│ asignaciones_revisores                        │
├───────────────────────────────────────────────┤
│ id (PK, SERIAL)                               │
│ documento_id (FK → documentos.id, CASCADE)    │
│ revisor_id (INT - ref user_db)                │
│ notificado (BOOLEAN, DEFAULT false)           │
│ fecha_asignacion (TIMESTAMP)                  │
│ UNIQUE(documento_id, revisor_id)              │
└───────────────────────────────────────────────┘

-- Auditoría de Cambios
┌───────────────────────────────────────────────┐
│ auditoria_documentos                          │
├───────────────────────────────────────────────┤
│ id (PK, SERIAL)                               │
│ documento_id (FK → documentos.id, CASCADE)    │
│ usuario_id (INT - ref user_db)                │
│ accion (VARCHAR - crear, subir_version,       │
│         devolver, aprobar, actualizar,        │
│         finalizar)                            │
│ descripcion (TEXT)                            │
│ datos_adicionales (JSON)                      │
│ fecha_accion (TIMESTAMP)                      │
└───────────────────────────────────────────────┘
```

---

### 3.3 Optimizaciones

#### Índices Estratégicos

```sql
-- documentos_db
CREATE INDEX idx_documentos_estado ON documentos(estado);
CREATE INDEX idx_documentos_creador ON documentos(usuario_creador_id);
CREATE INDEX idx_documentos_fecha ON documentos(fecha_creacion DESC);
CREATE INDEX idx_versiones_documento ON versiones_documento(documento_id, numero_version);
CREATE INDEX idx_revisiones_compound ON revisiones(documento_id, version_revisada, revisor_id);
CREATE INDEX idx_auditoria_documento ON auditoria_documentos(documento_id, fecha_accion DESC);

-- sancionatoria_db
CREATE INDEX idx_expedientes_encargado ON expedientes(encargado_id);
CREATE INDEX idx_expedientes_etapa ON expedientes(etapa_id);
CREATE INDEX idx_expedientes_estado ON expedientes(estado);
CREATE INDEX idx_involucrado_expediente ON involucrado_expediente(expediente_radicado);
CREATE INDEX idx_involucrados_documento ON involucrados(numero_documento, tipo_documento);

-- user_db
CREATE INDEX idx_usuarios_correo ON usuarios(correo);
CREATE INDEX idx_usuarios_rol ON usuarios(rol_id);
CREATE INDEX idx_notificaciones_usuario ON notificaciones(usuario_id, leida);
CREATE INDEX idx_auditoria_usuario ON auditoria(usuario_id, fecha DESC);
```

#### Consultas Optimizadas (SQLAlchemy)

```python
# Lazy loading vs Eager loading

# ❌ N+1 Problem
documentos = await db.execute(select(Documento))
for doc in documentos:
    versiones = doc.versiones  # Query adicional por documento!

# ✅ Eager loading con selectinload
stmt = select(Documento).options(
    selectinload(Documento.versiones),
    selectinload(Documento.revisiones),
    selectinload(Documento.asignaciones_revisores),
    selectinload(Documento.auditoria)
)
documentos = await db.execute(stmt)  # Solo 2 queries total
```

---

## 4. Flujos de Negocio

### 4.1 Gestión Documental

#### Estados y Transiciones

```
┌────────────────────────────────────────────────────────────┐
│           MÁQUINA DE ESTADOS - DOCUMENTO                   │
└────────────────────────────────────────────────────────────┘

                    ┌───────────────┐
                    │    CREAR      │
                    │  (v1 inicial) │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
              ┌────►│ en_revision   │
              │     └───────┬───────┘
              │             │
              │             ├─► Todos aprueban
              │             │   └─► ┌───────────┐
              │             │       │ aprobado  │
              │             │       └─────┬─────┘
              │             │             │
              │             │             ▼
              │             │       ┌────────────┐
              │             │       │finalizado  │
              │             │       └────────────┘
              │             │
              │             └─► Al menos 1 devuelve
              │                 └─► ┌───────────┐
              │                     │ rechazado │
              │                     └─────┬─────┘
              │                           │
              │                           ▼
              │                     ┌──────────────┐
              │                     │ Subir nueva  │
              │                     │ versión (v2) │
              │                     └──────┬───────┘
              │                            │
              └────────────────────────────┘
                      (vuelve a en_revision)
```

#### Flujo Completo de Creación

```
┌──────────────────────────────────────────────────────────────┐
│         FLUJO: CREACIÓN Y REVISIÓN DE DOCUMENTO              │
└──────────────────────────────────────────────────────────────┘

[FASE 1: CREACIÓN]
Usuario Creador
  ↓
1. POST /documents/create
   - nombre: "Manual de Procedimientos"
   - descripcion: "..."
   - tipo_archivo: "pdf"
   - archivo: <file>
   - revisores_ids: [10, 15, 23]
  ↓
2. app-docs procesa:
   ├─ Guardar archivo en uploads/documentos/
   ├─ INSERT INTO documentos (estado: en_revision, version_actual: 1)
   ├─ INSERT INTO versiones_documento (numero_version: 1)
   ├─ INSERT INTO asignaciones_revisores (3 registros)
   ├─ INSERT INTO auditoria_documentos (accion: crear)
   └─ Enviar 3 notificaciones a revisores
  ↓
3. Response: {documento_id: 42, estado: "en_revision"}

[FASE 2: REVISIÓN]
Revisor #1 (ID: 10)
  ↓
4. GET /documents/detail/42
   - Ver detalle completo
   - Descargar versión 1
  ↓
5. POST /documents/review/42
   - accion: "devolver"
   - comentarios: "Corregir sección 3.2"
  ↓
6. app-docs procesa:
   ├─ INSERT INTO revisiones (revisor_id: 10, estado: devuelto)
   ├─ UPDATE documentos SET estado = rechazado, numero_devoluciones++
   ├─ INSERT INTO auditoria_documentos (accion: devolver)
   └─ Notificar al creador
  ↓
7. Estado: rechazado (contador: 1/3 rechazos)

[FASE 3: CORRECCIÓN]
Usuario Creador
  ↓
8. POST /documents/upload-version/42
   - archivo: <file_corregido>
   - comentario: "Sección 3.2 corregida"
  ↓
9. app-docs procesa:
   ├─ INSERT INTO versiones_documento (numero_version: 2)
   ├─ UPDATE documentos SET version_actual = 2, estado = en_revision
   ├─ INSERT INTO auditoria_documentos (accion: actualizar)
   └─ Notificar a los 3 revisores (nueva versión disponible)
  ↓
10. Estado: en_revision (versión 2)

[FASE 4: APROBACIÓN]
Revisor #1 (ID: 10)
  ↓
11. POST /documents/review/42
    - accion: "aprobar"
    - comentarios: "Correcciones OK"
  ↓
Revisor #2 (ID: 15)
  ↓
12. POST /documents/review/42
    - accion: "aprobar"
  ↓
Revisor #3 (ID: 23)
  ↓
13. POST /documents/review/42
    - accion: "aprobar"
  ↓
14. app-docs verifica:
    ├─ COUNT revisiones aprobadas versión 2 = 3
    ├─ COUNT total revisores asignados = 3
    ├─ 3 == 3 → TODOS APROBARON
    ├─ UPDATE documentos SET estado = aprobado
    ├─ INSERT INTO auditoria_documentos (accion: aprobar)
    └─ Notificar al creador
  ↓
15. Estado FINAL: aprobado (puede pasar a finalizado manualmente)
```

---

### 4.2 Expedientes Sancionatorios

#### Flujo de Gestión

```
┌──────────────────────────────────────────────────────────────┐
│           FLUJO: EXPEDIENTE SANCIONATORIO                     │
└──────────────────────────────────────────────────────────────┘

[ETAPA 1: APERTURA]
Operador
  ↓
1. POST /sanctioning/file/create
   - nombre: "Caso deforestación Z"
   - descripcion: "..."
   - municipio_codigo: "05001"
  ↓
2. app-sancionatoria procesa:
   ├─ Generar radicado: EXP-20251205-0042
   ├─ INSERT INTO expedientes (etapa_id: 1, estado: activo)
   └─ Response: {radicado: "EXP-20251205-0042"}

[ETAPA 2: INVOLUCRADOS]
Operador
  ↓
3. POST /sanctioning/involved/create
   - numero_documento: 900123456
   - tipo_documento: "NIT"
   - digito_verificacion: "3"
   - nombre: "Empresa XYZ S.A."
   - expediente_radicado: "EXP-20251205-0042"
   - rol: "demandado"
  ↓
4. app-sancionatoria verifica:
   ├─ Calcular DV con algoritmo DIAN
   ├─ DV calculado == 3? ✓
   ├─ INSERT INTO involucrados
   ├─ INSERT INTO involucrado_expediente
   └─ Response: {involucrado_id: 152}

[ETAPA 3: FORMULACIÓN DE CARGOS]
Encargado
  ↓
5. POST /sanctioning/acto-admin/create
   - tipo: "formulacion_cargos"
   - numero: "FC-001-2025"
   - fecha: "2025-12-05"
   - descripcion: "..."
  ↓
6. Adjuntar documentos:
   POST /sanctioning/document/upload
   - archivo: "formulacion_cargos.pdf"
  ↓
7. Avanzar etapa:
   PATCH /sanctioning/file/{radicado}
   - etapa_id: 2  (Decisión de Fondo)

[ETAPA 4: DECISIÓN]
Encargado
  ↓
8. POST /sanctioning/decision/create
   - tipo_decision: "sancion"
   - descripcion: "Multa + Cierre"
  ↓
9. Notificaciones automáticas:
   ├─ Sistema genera alerta (7 días antes vencimiento)
   ├─ Email a involucrados
   └─ Notificación en sistema

[ETAPA 5: RECURSO (Opcional)]
Involucrado
  ↓
10. Presenta recurso de reposición
    ├─ Encargado recibe y procesa
    └─ Etapa: 3 (Recurso)

[ETAPA 6: CIERRE]
Encargado
  ↓
11. PATCH /sanctioning/file/{radicado}
    - estado: "cerrado"
  ↓
12. Archivo permanente en sistema
```

---

## 5. Implementación

### 5.1 Stack Tecnológico

#### Backend Core

```yaml
FastAPI:
  version: ">=0.100.0"
  features:
    - Async/await nativo
    - Validación con Pydantic
    - OpenAPI/Swagger auto-generado
    - Dependencias inyectables

SQLAlchemy:
  version: ">=2.0.0"
  mode: Async
  features:
    - ORM con AsyncSession
    - Migrations con Alembic
    - Eager loading (selectinload)
    - Relaciones optimizadas

PostgreSQL:
  version: ">=15.0"
  features:
    - JSON/JSONB fields
    - Full-text search (opcional)
    - Replicación (producción)
    - Índices parciales

python-jose:
  use: JWT encoding/decoding
  algorithm: HS256
  features:
    - Dual-key system
    - Payload encryption

httpx:
  use: HTTP client microservicios
  features:
    - AsyncClient
    - HTTP/2 support
    - Connection pooling
    - Timeout configuration
```

#### Frontend Core

```yaml
React:
  version: "19.1.0"
  features:
    - Hooks (useState, useEffect, useContext)
    - Functional components
    - React Router DOM 7.7
    - Context API para auth

TypeScript:
  version: "5.8+"
  strict: true
  features:
    - Type safety
    - Interfaces
    - Generics

TailwindCSS + DaisyUI:
  versions: "4.1 + 5.0"
  features:
    - Utility-first CSS
    - Componentes pre-diseñados
    - Temas dark/light
    - Responsive design

Vite:
  version: "7.0+"
  features:
    - HMR ultra-rápido
    - Build optimizado
    - Tree-shaking
    - Code splitting
```

---

### 5.2 Instalación

#### Prerrequisitos

```bash
# Sistema operativo
Windows 10/11, Linux (Ubuntu 20.04+), macOS

# Software requerido
PostgreSQL 15+
Python 3.11+
Node.js 18+ y npm
Git
```

#### Clonar Repositorio

```bash
git clone https://github.com/tu-org/apicorp.git
cd apicorp
```

#### Configurar Bases de Datos

```sql
-- Conectar a PostgreSQL como superusuario
psql -U postgres

-- Crear bases de datos
CREATE DATABASE user_db;
CREATE DATABASE sancionatoria_db;
CREATE DATABASE documentos_db;

-- Crear usuario específico (opcional pero recomendado)
CREATE USER apicorp_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE user_db TO apicorp_user;
GRANT ALL PRIVILEGES ON DATABASE sancionatoria_db TO apicorp_user;
GRANT ALL PRIVILEGES ON DATABASE documentos_db TO apicorp_user;

\q
```

#### Instalar Dependencias Backend

```bash
# Instalar dependencias globales
pip install -r requirements.txt

# O instalar por microservicio (desarrollo)
cd app-users
pip install fastapi uvicorn sqlalchemy asyncpg python-jose[cryptography] \
            python-multipart bcrypt pydantic python-dotenv httpx

cd ../app-sancionatoria
pip install fastapi uvicorn sqlalchemy asyncpg python-jose[cryptography] \
            pydantic python-dotenv httpx

cd ../app-docs
pip install fastapi uvicorn sqlalchemy asyncpg python-jose[cryptography] \
            python-multipart pydantic python-dotenv httpx aiofiles

cd ../api-gateway
pip install fastapi uvicorn python-jose[cryptography] python-dotenv httpx
```

#### Instalar Dependencias Frontend

```bash
cd frontend
npm install
```

---

### 5.3 Configuración

#### Variables de Entorno

**app-users/.env**
```env
DATABASE_URL=postgresql+asyncpg://apicorp_user:secure_password@localhost:5432/user_db
SECRET_KEY=<generar con: openssl rand -hex 32>
SECRET_KEY_GATEWAY=<DEBE SER IDÉNTICA EN api-gateway>
JWT_ALGORITHM=HS256

# Email SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
```

**app-sancionatoria/.env**
```env
DATABASE_URL=postgresql+asyncpg://apicorp_user:secure_password@localhost:5432/sancionatoria_db
SECRET_KEY=<generar única para este servicio>
SECRET_KEY_GATEWAY=<MISMA QUE app-users>
JWT_ALGORITHM=HS256
GATEWAY_URL=http://localhost:8000
```

**app-docs/.env**
```env
DATABASE_URL=postgresql+asyncpg://apicorp_user:secure_password@localhost:5432/documentos_db
SECRET_KEY=<generar única para este servicio>
SECRET_KEY_GATEWAY=<MISMA QUE app-users>
JWT_ALGORITHM=HS256
GATEWAY_URL=http://localhost:8000
PERMISO_CREADOR_DOC=documento_crear
PERMISO_REVISION_DOC=documento_revisar
```

**api-gateway/.env**
```env
SECRET_GATEWAY=<generar única>
SECRET_KEY_GATEWAY=<MISMA QUE app-users>
JWT_ALGORITHM=HS256
```

**frontend/.env** (opcional)
```env
VITE_API_URL=http://localhost:8000
```

#### Generar Secret Keys

```bash
# Linux/macOS
openssl rand -hex 32

# Windows (PowerShell)
-join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### 5.4 Despliegue

#### Desarrollo Local

```bash
# Terminal 1: API Gateway
cd api-gateway
uvicorn main:app --reload --port 8000

# Terminal 2: app-users
cd app-users
uvicorn main:app --reload --port 8002

# Terminal 3: app-sancionatoria
cd app-sancionatoria
uvicorn main:app --reload --port 8001

# Terminal 4: app-docs
cd app-docs
uvicorn main:app --reload --port 8003

# Terminal 5: Frontend
cd frontend
npm run dev
```

**Acceder a:**
- Frontend: http://localhost:5173
- Gateway: http://localhost:8000
- Swagger Users: http://localhost:8002/docs
- Swagger Sancionatoria: http://localhost:8001/docs
- Swagger Docs: http://localhost:8003/docs

#### Estructura de Archivos

```
uploads/
├── documentos/           # Archivos de app-docs
│   ├── 20251205_120530_manual.pdf
│   └── 20251205_143022_politicas.docx
└── expedientes/          # Archivos de app-sancionatoria
    └── EXP-20251205-0042/
        ├── formulacion_cargos.pdf
        └── decision_fondo.pdf
```

---

## 📚 Documentación Adicional

- **EJEMPLO_USO_PERMISOS.md**: Guía completa del sistema de permisos con ejemplos de código
- **app-docs/GUIA_APLICACION.md**: Documentación específica del módulo de documentos
- **app-sancionatoria/GUIA_APLICACION.md**: Documentación específica del módulo sancionatorio

---

## 🐛 Troubleshooting

### Error: Cannot find SECRET_KEY_GATEWAY

**Causa:** Variable de entorno no configurada o servidor no reiniciado.

```bash
# Verificar que existe
cat app-users/.env | grep SECRET_KEY_GATEWAY
cat api-gateway/.env | grep SECRET_KEY_GATEWAY

# Deben ser idénticas
# Reiniciar ambos servicios
```

### Error 403: No tienes permiso

**Diagnóstico:**
```sql
-- Verificar permisos del usuario
SELECT u.correo, r.name, p.name, p.path 
FROM usuarios u
JOIN roles r ON u.rol_id = r.id
JOIN roles_permisos rp ON r.id = rp.rol_id
JOIN permisos p ON rp.permiso_id = p.id
WHERE u.id = <user_id>;
```

### Frontend no conecta con Backend

**Verificar CORS:**
```python
# En main.py de cada servicio
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Ajustar según necesidad
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📄 Licencia

Proyecto propietario - ApiCorp © 2025

---

**Última actualización:** Diciembre 5, 2025  
**Versión:** 1.0.0  
**Mantenedor:** Equipo de Desarrollo ApiCorp
