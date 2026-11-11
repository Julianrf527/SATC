# Arquitectura del Sistema SATC

**Sistema:** SATC (Sistema de Administración de Trámites de Corpochivor)
**Documento:** Arquitectura Técnica y Diseño del Sistema  
**Versión:** 2.2  
**Fecha:** 19 de octubre de 2026  
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
- **Deployment:** Docker Compose con orquestación de 19 contenedores (octubre 2026: se agregan `app-recurso` y `postgres-recurso`)
- **Microservicios de dominio:** 6 (usuarios, sancionatorio, documentos, involucrados, infracciones y Concesiones de Aguas)
- **Recursos:** 3.0 GB RAM, 4 vCPUs recomendados (dimensionamiento validado en junio 2026 con 5 microservicios; ver nota en [Distribución de Recursos por Contenedor](#distribución-de-recursos-por-contenedor))

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

> **Diagramas pendientes de actualizar (octubre 2026).** Las tres imágenes de esta sección y el mapa de puertos
> (`assets/*.jpg`) corresponden a junio de 2026: muestran 5 microservicios y 5 bases PostgreSQL. **No incluyen**
> el microservicio `app-recurso` (puerto 8006), su base `recurso_db` en `postgres-recurso`, la ruta `/recurso` del
> gateway ni su conexión con app-users, app-docs y app-involved. El mapa de puertos tampoco refleja el puerto interno
> 8080 de nginx. Mientras se actualizan, la fuente vigente son las tablas de este documento.

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
| **app-infraction** | Infracciones | Catálogo y operación de infracciones; flujo propio de revisión de informes técnicos | PostgreSQL `infracciones_db` |
| **app-recurso** | Concesiones de Aguas Superficiales | Expedientes de concesión, etapas, actos, comunicaciones y notificaciones; flujo propio de revisión de documentos | PostgreSQL `recurso_db` |

### Servicios de Infraestructura Compartida

- **Redis:** caché y sesiones de usuario (sesión única por usuario).
- **MinIO:** almacenamiento de objetos para documentos (Files). Imagen comunitaria `pgsty/minio` fijada por versión y digest (ver [Storage](#storage)).
- **ClamAV:** análisis antivirus previo a persistencia (puerto 3310).
- **PostgreSQL por servicio:** aislamiento de datos y evolución independiente.
- **MailHog:** servicio de captura de correos para desarrollo/testing (no envía emails reales). No está incluido en el `docker-compose.yml` vigente.
- **Backup service:** cronjob que respalda todas las bases de datos periódicamente (incluida `recurso_db`, script `scripts/backup-all.sh`) y MinIO.

### Microservicio app-recurso (Concesiones de Aguas Superficiales) — octubre 2026

Microservicio hermano de sancionatorio e infracciones para el trámite de concesiones de aguas superficiales. Sigue el mismo
stack (Python/FastAPI, Gunicorn con 4 workers Uvicorn, SQLAlchemy asíncrono) y el patrón *database per service*.

| Elemento | Valor |
| --- | --- |
| Carpeta / servicio compose | `app-recurso/` · servicio `app-recurso` (contenedor `satc-app-recurso`) |
| Puerto interno | **8006** (healthcheck `GET /health`) |
| Base de datos | `recurso_db` en el servicio `postgres-recurso` (contenedor `satc-postgres-recurso`, volumen `postgres-recurso-data`), sin puerto al host |
| Identidad entre servicios | `recurso-service`, con secreto propio `RECURSO_SERVICE_SECRET` |
| Ruta del gateway | prefijo **`/recurso`** → `http://app-recurso:8006` (`RECURSO_ROUTE`) |
| Rutas SPA | `/recurso/manage` (Gestionar), `/recurso/consult` (Consulta), `/recurso/my-reports` (Mis informes); nginx las envía al frontend |
| Permisos | `recurso_*` (9 permisos; ver `MANUAL_PERMISOS_SATC.md`) |
| Límites | 2.0 CPU / 450 MB (reserva 1.0 CPU / 225 MB) |

**Dependencias con otros servicios** (llamadas directas, no a través del gateway, con `X-Service-Token` de `recurso-service`):

- **app-users** (`USER_SERVICE_URL`): verificación de permisos de los usuarios, datos de funcionarios (abogados, técnicos,
  revisores) y notificaciones internas (tipo `recurso_doc`). app-users acepta a `recurso-service` como caller.
- **app-docs** (`DOCS_SERVICE_URL`): almacenamiento de los archivos (cargue, hash, antivirus). app-recurso solo guarda el
  identificador del archivo y lleva el conteo de usos (`numero_usos`). app-docs acepta los permisos `recurso_*` para
  subir y descargar archivos y acepta a `recurso-service` como caller.
- **app-involved** (`INVOLVED_SERVICE_URL`, por defecto `http://app-involved:8004`): solicitantes, terceros intervinientes y
  representantes legales; app-recurso guarda solo sus ids. app-involved acepta los permisos de gestión de Concesiones (`recurso_gestionar`, `recurso_super_gestion`) y a `recurso-service`.

En `docker-compose.yml`, `app-recurso` arranca cuando `postgres-recurso` y `app-users` están *healthy*.

#### Modelo de datos (resumen)

El modelo vigente, generado desde los modelos SQLAlchemy desplegados, está en
`app-recurso/plan trabajo/concesiones_dbml_actual.txt` (formato DBML). Se organiza en cinco grupos:

| Grupo | Tablas |
| --- | --- |
| Información base | `expediente`, `expediente_fuente`, `expediente_uso`, `expediente_involucrado` (solicitantes y terceros intervinientes), catálogos `municipio`, `vereda`, `tipo_fuente`, `fuente` |
| Actos y publicidad | `acto_administrativo` (tipo de acto, clase AUTO/RES, número y fecha), `comunicacion`, `notificacion`, `tipo_notificacion` |
| Etapas | `acto_admite`, `concepto_tecnico`, `requerimiento`, `decision`, `recurso_reposicion`, `memorias_calculo`, `subsanacion`, `informe_usuario`, `recibo_satisfaccion_obras`, `documentos_anexos` |
| Revisión de documentos | `documento_proceso`, `documento_proceso_version`, `documento_proceso_revision`, `documento_proceso_revisor`, `documento_proceso_auditoria` |
| Auditoría | `auditoria` |

Las tablas editables tienen columna `version` para bloqueo optimista. Los campos que apuntan a otros servicios
(archivos de app-docs, personas de app-involved, funcionarios de app-users) son referencias lógicas por id, sin llave
foránea entre bases.

#### Proceso propio de revisión de documentos

Los documentos que se proyectan en cada etapa (autos, requerimientos, decisión, actos, conceptos técnicos) se revisan
**dentro de app-recurso**, en las tablas `documento_proceso*`, construidas sobre el módulo compartido
`satc_shared.review_process` (el mismo que usa app-infraction para sus informes técnicos). app-docs solo almacena los archivos.

- Hay un proceso por fila de etapa; el `tipo_documento` define la cadena de pasos y cada paso es un conjunto de permisos
  de revisor que deben revisar **todos**, en cualquier orden.
- Estados: pendiente de carga → en revisión → devuelto / aprobado para firma → aprobado (versión firmada en PDF).
- Endpoints genéricos `/recurso/revision-documentos/*` (versiones, revisiones, historial, auditoría, descargas) y la
  bandeja `/recurso/mis-documentos` (Mis informes), con filtros y paginación en el servidor.

#### Concurrencia e integridad de archivos

- **Bloqueo pesimista** (`SELECT … FOR UPDATE` sobre el expediente) en las transiciones de etapa.
- **Bloqueo optimista** (columna `version`) en las ediciones: si otra persona modificó el registro, respuesta 409.
- **Asignación atómica** de "Asignarme para diligenciar" (`UPDATE … WHERE encargado IS NULL`): dos solicitudes
  simultáneas terminan en una asignación y un 409.
- **Compensación de usos de archivos** (`services/usos_archivos.py`): el uso del archivo en app-docs se suma antes del
  commit; si la operación falla, se resta exactamente lo sumado para no dejar contadores inflados.

### Módulo compartido `shared/satc_shared`

Paquete Python que se copia en la imagen de cada microservicio (contexto de build `shared`):

| Módulo | Uso |
| --- | --- |
| `satc_shared.review_process` | Motor genérico de flujos de revisión por pasos (modelos, máquina de estados, servicio). Lo usan app-infraction (informes técnicos), app-recurso (documentos de Concesiones) y app-docs (flujo genérico de documentos). |
| `satc_shared.alertas` | Paginación y filtros en servidor de la pestaña Alertas (`paginar_alertas`): lista plana ordenada por urgencia y % de avance, filtros por radicado, estado y tipo, máximo 100 por página. Lo usan app-sancionatoria y app-infraction. |
| `satc_shared.clients` | Clientes HTTP directos entre servicios (`UsersClient`, `FilesClient`, `InvolvedClient`). |
| `satc_shared.auth` | Firma y verificación del `X-Service-Token` (JWT de servicio, vigencia 5 minutos) con un secreto por identidad: `sanctioning-service`, `infraction-service`, `recurso-service`, `docs-service`, `involved-service`. |

### Cálculo de alertas en bloque (octubre 2026)

En app-sancionatoria y app-infraction las alertas de vencimiento de todos los expedientes se calculan **en bloque**
(`calcular_alertas_expedientes` en `services/alertas.py`) con un número fijo de consultas, sin importar cuántos
expedientes haya, en lugar de una consulta por expediente. Lo usan la pestaña Alertas y el programador de alertas
(`services/alertas_scheduler.py`). La pestaña Alertas recibe la respuesta ya filtrada y paginada desde el servidor
(`satc_shared.alertas`) y admite el alcance "Mis expedientes / Todos".

### Sincronización del catálogo de permisos al arrancar app-users (octubre 2026)

El catálogo único de permisos está en `app-users/db/permission_catalog.py` (32 permisos con ruta de menú y descripción,
17 dependencias y renombres). En cada arranque, app-users ejecuta `sync_permission_catalog()`
(`db/permission_sync.py`) en una sola transacción protegida con `pg_advisory_xact_lock` (los workers de Gunicorn corren
en serie). La rutina es idempotente:

- agrega la columna `descripcion` y la tabla `permiso_requiere` si no existen;
- aplica los renombres sobre la misma fila (los roles conservan el permiso);
- inserta los permisos faltantes y los otorga a los roles que tenían todos los permisos;
- llena ruta de menú y descripción solo si están vacías (respeta lo editado en pantalla);
- deja `permiso_requiere` igual a las dependencias del catálogo;
- nunca borra permisos ni corrige roles: solo registra en el log los roles que incumplen dependencias.

Con esto, crear o renombrar permisos ya no requiere SQL manual en el servidor.


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
| **app-recurso**     | 1                 | Gestión de Concesiones de Aguas             |

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
Total configurado (octubre 2026): 27 workers Gunicorn

api-gateway:     6 workers
app-users:       4 workers
app-sanctioning: 4 workers
app-docs:        1 worker
app-involved:    4 workers
app-infraction:  4 workers
app-recurso:     4 workers
```

> Valores tomados del `CMD` de cada `Dockerfile`. La tabla de capacidad siguiente corresponde a la prueba de
> carga de junio de 2026 (16 workers de los servicios principales) y no se ha repetido con la configuración actual.

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
  - Nginx Reverse Proxy (nginx:alpine, puerto interno 8080 → host 8000)
- **Exposición:** Solo el proxy en puerto 8000 del host
- **Acceso:** Disponible para usuarios en la LAN

#### Red Privada (`satc-private`)

- **Propósito:** Orquestación interna y datos
- **Componentes:**
  - API Gateway (FastAPI, orquestación)
  - Microservicios: App_Usuarios, App_Sancionatoria, App_Documentos, App_Involucrados, App_Infracciones, App_Recurso (Concesiones de Aguas)
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
| **Nginx-LB**        | Public + Private | 8080  | 8000        | HTTP      | ✓ Desde host (LAN) |
| **Frontend SPA**    | Public     | 80          | —           | HTTP      | ✓ Vía nginx       |
| **API Gateway**     | Private    | 8000        | —           | HTTP      | ✓ Vía nginx       |
| **app-users**       | Private    | 8001        | —           | HTTP      | ✓ Vía gateway     |
| **app-sanctioning** | Private    | 8002        | —           | HTTP      | ✓ Vía gateway     |
| **app-docs**        | Private    | 8003        | —           | HTTP      | ✓ Vía gateway     |
| **app-involved**    | Private    | 8004        | —           | HTTP      | ✓ Vía gateway     |
| **app-infraction**  | Private    | 8005        | —           | HTTP      | ✓ Vía gateway     |
| **app-recurso**     | Private    | 8006        | —           | HTTP      | ✓ Vía gateway     |
| **PostgreSQL** (×6) | Private    | 5432        | —           | TCP       | ✗ No expuesto    |
| **Redis**           | Private    | 6379        | —           | TCP       | ✗ No expuesto    |
| **MinIO**           | Private    | 9000/9001   | —           | HTTP      | ✗ No expuesto    |
| **ClamAV**          | Private    | 3310        | —           | TCP       | ✗ No expuesto    |
| **MailHog**         | Private    | 8025 (UI)   | —           | HTTP      | ✗ Solo desarrollo (no incluido en el compose vigente) |

#### Flujo de Solicitudes

```
1. Cliente Externo
   └─> GET http://host:8000/
       └─> Nginx-LB (8000:8080)
           ├─> / y rutas SPA            → Frontend (80)
           │     (incluye /infraction/(manage|consult|alerts|assign_manage|reports|my-reports)
           │      y /recurso/(manage|consult|my-reports))
           └─> /(users|sanctioning|documents|infraction|recurso|involveds)/*
                                        → API Gateway (8000), que enruta por el primer segmento:
               ├─> /users/*             → app-users (8001)
               ├─> /sanctioning/*       → app-sanctioning (8002)
               ├─> /documents/*         → app-docs (8003)
               ├─> /involveds/*         → app-involved (8004)
               ├─> /infraction/*        → app-infraction (8005)
               └─> /recurso/*           → app-recurso (8006)
```

> Prefijos según `MICROSERVICES` de `api-gateway/main.py` y la `location` de `nginx/nginx.conf`.
> Las llamadas entre microservicios no pasan por el gateway: van directas (`app-users:8001`,
> `app-docs:8003`, `app-involved:8004`) con `X-Service-Token` firmado con el secreto de cada identidad.

#### Servicios Compartidos (Red Privada)

```
Microservicios ──────────> PostgreSQL 5432 (6 instancias, una por microservicio con datos)
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

# Extracto simplificado. Configuración vigente: nginx/nginx.conf (escucha en 8080).
server {
    listen 8080;

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

Límites y reservas vigentes según `deploy.resources` de `docker-compose.yml` (octubre 2026). En octubre se
ajustaron los límites de memoria según el uso real observado: `api-gateway` 900 → 384 MB, `app-users`
600 → 450 MB, `app-docs` 128 → 256 MB, `minio` 192 → 256 MB y `nginx-lb` 128 → 64 MB.

| Contenedor           | CPU Límite | RAM Límite | RAM Reservada |
| -------------------- | ---------- | ---------- | ------------- |
| nginx-lb             | 1.0        | 64 MB      | 64 MB         |
| frontend             | 0.5        | 64 MB      | 32 MB         |
| api-gateway          | 4.0        | 384 MB     | 256 MB        |
| app-users            | 2.0        | 450 MB     | 200 MB        |
| app-sancionatoria    | 2.0        | 450 MB     | 225 MB        |
| app-docs             | 0.5        | 256 MB     | 64 MB         |
| app-involved         | 1.0        | 384 MB     | 160 MB        |
| app-infraction       | 2.0        | 450 MB     | 225 MB        |
| app-recurso          | 2.0        | 450 MB     | 225 MB        |
| postgres-users       | 1.0        | 200 MB     | 100 MB        |
| postgres-sanctioning | 2.0        | 128 MB     | 64 MB         |
| postgres-docs        | 1.5        | 96 MB      | 48 MB         |
| postgres-involved    | 1.0        | 96 MB      | 48 MB         |
| postgres-infraction  | 1.5        | 200 MB     | 100 MB        |
| postgres-recurso     | 1.5        | 200 MB     | 100 MB        |
| redis                | 1.0        | 256 MB     | 128 MB        |
| minio                | 2.0        | 256 MB     | 96 MB         |
| clamav               | 2.0        | 1400 MB    | 700 MB        |
| backup-service       | 0.5        | 128 MB     | 64 MB         |
| **TOTAL**            | **29.0**   | **5912 MB (~5.8 GB)** | **2899 MB (~2.8 GB)** |

> Los límites son topes por contenedor, no consumo simultáneo: la suma de límites de CPU supera los vCPUs del
> host a propósito. El consumo real medido en junio de 2026 (≈2.5 GB con 5 microservicios) no se ha vuelto a
> medir con `app-recurso`; la reserva total (~2.8 GB) es la referencia mínima de memoria para el host.

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

**MinIO (imagen comunitaria `pgsty/minio`, versión fijada):**

- Imagen: `pgsty/minio:RELEASE.2026-08-04T00-00-00Z` fijada además por digest `sha256`, para que nunca se actualice sola.
- Por qué: MinIO Inc. dejó de publicar la imagen comunitaria `minio/minio` (octubre de 2025), por lo que `minio/minio:latest`
  ya no recibe versiones. `pgsty/minio` es un fork comunitario del mismo código (licencia AGPLv3).
- Verificación del cambio (16/10/2026): con una copia de los datos de producción, los 48 documentos almacenados resultaron
  idénticos byte a byte. Se conserva una copia de la imagen anterior en `backups/minio-20261016/` para rollback.
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

# Identidades entre servicios (un secreto por caller; octubre 2026)
RECURSO_SERVICE_SECRET=<recurso-service-secret>

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

_Última actualización: 19 de octubre de 2026_  
_Versión: 2.2_  
_Clasificación: Documentación Técnica Interna_
