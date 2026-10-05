# Auditoría de permisos backend: SATC (octubre 2026)

**Fecha:** 2026-10-04 · **Rama:** `refactor/file-flow` (árbol de trabajo sin commit) · **Alcance:** api-gateway, app-users, app-sancionatoria, app-infraction, app-docs, app-involved.

> **Ojo con la foto.** Mientras se hacía esta auditoría, otros dos agentes estaban editando `app-sancionatoria`, `frontend/src/modules/app-sancionatorio`, `shared/review_process`, `app-docs/routes/{documentos,revision}.py` y `app-infraction/*revision_informes*`. Lo que aquí se dice de esos archivos refleja su estado al 2026-10-04 cerca de las 11:45. Hay que revisarlo de nuevo cuando esos cambios se integren.

## 1. Modelo de autenticación (cómo funciona hoy)

| Capa | Qué valida | Qué NO valida |
|---|---|---|
| **api-gateway** (`/{service}/{path}`) | Cookie JWE, sesión en Redis (jti), rate limit, traversal. Inyecta `X-Gateway-Token`, `X-Gateway-User-Id` y `X-Gateway-Role-Id`, y descarta esas cabeceras si vienen del cliente (`TRUST_HEADERS`). | **Ningún permiso por ruta.** Cualquier usuario con sesión llega a cualquier endpoint no público. |
| `PUBLIC_ROUTES` (por servicio) | No exige sesión. Aun así inyecta `X-Gateway-Token` (sin user-id). | |
| Backend `verify_gateway_token` | Que la petición venga del gateway y traiga user-id y rol-id. | Permisos. |
| Backend `verify_permission(user, permiso)` | Consulta a app-users (`/role/verify`) con caché. | |
| Backend, chequeo por propiedad | `encargado_id` / `abogado_responsable_id == user_id`, creador o revisor asignado. | Que el usuario conserve el permiso del módulo. |
| `verify_service_token` | JWT firmado por el servicio que llama (`EXPECTED_CALLERS`). No acepta `X-Gateway-Token`. | |

**Conclusión del modelo:** el único control de autorización real está en el backend. El frontend (`RequirePermission` / `inferPermissionFromPath` en `App.tsx`) solo oculta pantallas. Todo endpoint que no llame a `verify_permission` ni haga un chequeo de propiedad queda **abierto a cualquier usuario autenticado**.

### Roles actuales (para evaluar el riesgo de bloqueo)

`app-users/db/seeds.py` solo siembra el rol **admin** (todos los permisos) y el usuario administrador. Los demás roles se crean desde la UI. En la BD **local** (`user_db`) hay:

| Rol | Permisos |
|---|---|
| 1 `admin` | todos (23) |
| 2 `sub admin` | documento_crear, documento_gestionar, infraccion_alertas, infraccion_consultar, infraccion_gestionar, infraccion_informes_subir |

**Los roles de producción (VM) no se pudieron verificar.** Antes de desplegar cualquier cierre, ejecutar en la VM:

```sql
SELECT r.id, r.nombre, string_agg(p.nombre, ', ' ORDER BY p.nombre)
FROM rol r LEFT JOIN rol_permiso rp ON rp.rol_id = r.id LEFT JOIN permiso p ON p.id = rp.permiso_id
GROUP BY r.id, r.nombre ORDER BY r.id;
```

Úsese para confirmar que todo rol que entra a una pantalla tiene el permiso que se va a exigir en el backend. Por ejemplo, un rol con `infraccion_gestionar` pero sin `infraccion_consultar` no puede abrir expedientes ajenos, y eso es correcto.

### Pantallas del frontend y el permiso que exigen (`App.tsx`)

| Ruta | Permiso | Ruta | Permiso |
|---|---|---|---|
| /user/role | admin_roles_y_permisos | /infraction/manage | infraccion_gestionar |
| /user/add | admin_registrar_usuarios | /infraction/consult | infraccion_consultar |
| /user/manage | admin_gestionar_usuarios | /infraction/alerts | infraccion_alertas |
| /file/manage | sancionatorio_gestionar | /infraction/assign_manage | infraccion_asignar |
| /file/consult | sancionatorio_consultar | /infraction/reports | infraccion_asignar_informes |
| /file/alerts | sancionatorio_alertas | /infraction/my-reports | infraccion_informes_subir \| infraccion_informes_revisar |
| /file/assign_manage | sancionatorio_asignar | /audit/users | auditoria_usuarios |
| /involved/manage | involucrado_gestionar | /audit/files | auditoria_expedientes |
| /document/manage | documento_gestionar | /audit/involved | auditoria_involucrados |
| | | /audit/infractions | auditoria_infracciones |

En los componentes, el único control por botón es `infraccion_cargue` (`CargueManualInforme.tsx`, `Visita.tsx`).

---

## 2. Resumen de severidades

| Servicio | Endpoints | CRÍTICO | ALTO | MEDIO | OK |
|---|---|---|---|---|---|
| api-gateway | 2 (proxy, health) + configuración | 0 | 0 | 1 | 1 |
| app-users | 32 | 0 | 0 | 3 | 29 |
| app-sancionatoria | 65 | 4 | 18 | 33 | 10 |
| app-infraction (tras la Tarea 1) | 69 | 0 | 8 | 28 | 33 |
| app-docs | 16 | 1 | 0 | 2 | 13 |
| app-involved | 7 | 0 | 0 | 0 | 7 |
| **Total** | **191** | **5** | **26** | **67** | **93** |

Antes de la Tarea 1, `app-infraction/routes/file_query.py` tenía 4 hallazgos ALTO y 3 MEDIO. Ya están corregidos (sección 4.4).

Criterios:

- **CRÍTICO**: escritura o lectura de datos sensibles sin ningún permiso en el backend.
- **ALTO**: lectura de datos de negocio sin permiso.
- **MEDIO**: chequeo por propiedad sin permiso, o inconsistencias.
- **OK**: hay permiso, o el endpoint es de servicio, un catálogo inocuo o autoservicio.

---

## 3. Hallazgos ordenados por severidad

### CRÍTICO

| # | Endpoint (vía gateway) | Problema | Pantalla que lo usa | Permiso propuesto | Riesgo de bloqueo |
|---|---|---|---|---|---|
| C1 | `GET /documents/files/download/{file_id}` | `verify_internal_access` acepta `X-Gateway-Token`, así que **cualquier usuario autenticado descarga cualquier archivo del sistema** (IDs secuenciales). Es un IDOR sobre todos los documentos de sancionatorio, infracciones y documentos. | `shared/lib/documentViewer.ts`: todas las pestañas de etapas, actos y documentos | A corto plazo: exigir **al menos un permiso de módulo** (sancionatorio_gestionar/consultar, infraccion_gestionar/consultar/informes_*, documento_crear/revisar). A mediano plazo: URL de descarga firmada y de corta vida, emitida por el servicio dueño del recurso, que sí sabe a qué expediente pertenece el archivo. | **Alto si se cierra mal.** Todos los visores dependen de este endpoint. La versión "cualquier permiso de módulo" no bloquea a admin ni a sub admin. |
| C2 | `POST /sanctioning/expediente/add` | Crea expedientes sin verificar ningún permiso. Infracciones sí exige `infraccion_gestionar`. | `/file/manage` (NuevoExpediente) | `sancionatorio_gestionar` | Ninguno: la pantalla ya lo exige. |
| C3 | `POST /sanctioning/stage/doc-attached/{etapa_id}` | Adjunta un documento a **cualquier etapa de cualquier expediente**, sin permiso ni propiedad. Además incrementa `numero_usos` de un `file_id` arbitrario. | `/file/manage` (etapas/document/Document.tsx) | `sancionatorio_gestionar` y ser el encargado del expediente de la etapa (igual que `_post_etapa`) | Ninguno para el encargado. |
| C4 | `PUT /sanctioning/stage/doc-attached/{etapa_id}/{documento_id}` | Igual que C3: reemplaza el archivo de un anexo ajeno. | `/file/manage` | ídem | ídem |
| C5 | `DELETE /sanctioning/stage/doc-attached/{etapa_id}/{documento_id}` | Igual que C3: borra anexos de expedientes ajenos. | `/file/manage` | ídem | ídem |

### ALTO

| # | Endpoint | Problema | Pantalla | Permiso propuesto | Riesgo de bloqueo |
|---|---|---|---|---|---|
| A1 | `GET /sanctioning/expediente/get/all` | Lista **todos** los expedientes sancionatorios. Es el mismo caso que `/infraction/expedientes/todos`. | `/file/consult` | `sancionatorio_consultar` (agregarlo a `app-sancionatoria/core/permission.py`, que hoy no lo tiene) | Ninguno según la pantalla |
| A2 | `GET /sanctioning/stage/full/{id}` | Datos completos de cualquier expediente. | DetalleExpediente (`/file/manage` y `/file/consult`) | `sancionatorio_consultar`, o `sancionatorio_gestionar` + encargado (mismo patrón que la Tarea 1) | Ninguno |
| A3 | `GET /sanctioning/expediente/full/{id}` | Igual que A2. No se encontró consumidor en el frontend. | — | ídem, o eliminarlo | Ninguno |
| A4 | `GET /sanctioning/expediente/get` | Lista todos los expedientes, más los usuarios con su número de documento. | `/file/assign_manage` (EncargadoExpedienteLayout) | `sancionatorio_asignar` | Ninguno |
| A5–A14 | `GET /sanctioning/stage/{investigation,measure,start-process,cessation,formulation,opening,closing,decision,resource,execution}/{id}` (10) | `_get_etapa` usa `require_owner=False`: solo comprueba que el expediente exista. | DetalleExpediente | `sancionatorio_consultar`, o `sancionatorio_gestionar` + encargado. Hacerlo dentro de `get_expediente_con_permiso(require_owner=False)` para cubrir los 10 de una vez. | Ninguno |
| A15 | `GET /sanctioning/expediente/download-all/{id}` | PDF con todos los documentos de cualquier expediente. **El código lo marca como "intencionalmente público"**, así que es una decisión explícita. | DetalleExpediente | Replantear: `sancionatorio_consultar` o encargado | Hay que confirmar la decisión con el negocio |
| A16 | `GET /sanctioning/involved/involved-list/{expediente_id}` | Datos personales de los involucrados de cualquier expediente. | InformacionExpediente | `sancionatorio_consultar`, o gestionar + encargado | Ninguno |
| A17 | `GET /sanctioning/involved/file-list/{involved_id}` | Expedientes en los que aparece una persona: permite perfilarla. | (no se encontró consumidor directo) | `sancionatorio_consultar` o `involucrado_gestionar` | Ninguno |
| A18 | `POST /sanctioning/alerts/send-weekly-report` | **Cualquier usuario dispara el envío masivo de correos de alertas.** No lo usa el frontend. | — | Pasarlo a service-token, o exigir `admin_*` / `sancionatorio_alertas`. Mejor aún, eliminarlo. | Ninguno |
| A19 | `GET /infraction/expedientes/descargar/{id}` | PDF completo de cualquier expediente de infracción. | DetalleInfraccion (consulta y gestión) | `infraccion_consultar`, o `infraccion_gestionar` + encargado (como `/completo`) | Ninguno para admin ni sub admin |
| A20 | `GET /infraction/involucrados/expediente/{id}` | Datos personales de los involucrados de cualquier expediente. | InformacionInfraccion, InvolucradosExpediente | ídem A19 | Ninguno |
| A21 | `GET /infraction/involucrados/{id}/expedientes` | Expedientes de una persona. | (sin consumidor claro) | `infraccion_consultar` o `involucrado_gestionar` | Ninguno |
| A22 | `GET /infraction/etapas/respuesta/{id}` | Etapa de respuesta de cualquier expediente. | DetalleInfraccion | ídem A19 | Ninguno |
| A23 | `GET /infraction/etapas/informe-tecnico/{id}/{tipo}` | Solo comprueba que el expediente exista. | InformeTecnicoEtapa (dentro de DetalleInfraccion) | ídem A19. Si alguna vez se abre desde "Mis informes", añadir profesional o revisor asignado. | Bajo |
| A24 | `GET /infraction/etapas/concepto/{id}` | Sin control. | DetalleInfraccion | ídem A19 | Ninguno |
| A25 | `GET /infraction/etapas/cierre/{id}` | Sin control. | DetalleInfraccion | ídem A19 | Ninguno |
| A26 | `GET /infraction/etapas/migracion/medida/{radicado}` | Medida preventiva e informe de visita por radicado, sin control. | Sancionatorio (`app-sancionatorio/api/etapas.ts`) | `sancionatorio_gestionar` o `infraccion_consultar` | **Un rol con sancionatorio_gestionar pero sin permisos de infracción quedaría bloqueado si solo se exige `infraccion_consultar`.** Hay que aceptar los dos. |

### MEDIO

**Chequeo por propiedad sin permiso de módulo.** Se valida que el usuario sea el encargado, pero no que tenga `*_gestionar`. Si a alguien le quitan el permiso y no le reasignan sus expedientes, sigue pudiendo modificarlos llamando a la API. Propuesta común: añadir `verify_permission(user, *_gestionar)` dentro de `get_expediente_con_permiso` cuando `require_owner=True`. No bloquea a nadie, porque solo se le asignan expedientes a quien tiene el permiso de gestión.

| # | Servicio | Endpoints |
|---|---|---|
| M1 | sancionatoria | `POST/PUT/DELETE /acto/acto-admin`, `/acto/communication`, `/acto/notificacion` (9) |
| M2 | sancionatoria | `POST/PUT /stage/{investigation, measure×2, start-process, cessation×2, formulation×2, opening, closing, decision×2, resource, execution×2}` (15) |
| M3 | sancionatoria | `PUT /expediente/{id}/basic-data`, `PATCH /expediente/{id}/archive` (2) |
| M4 | sancionatoria | `POST/DELETE /involved/involved-file` (2) |
| M5 | sancionatoria | `POST /expediente/filter` y `GET /expediente/{encargado_id}`: propios, sin `sancionatorio_gestionar`. `filter` no tiene alcance "todos" (infracciones sí) (2) |
| M6 | sancionatoria | `GET /expediente/alerts/all`, `GET /expediente/alerts/{id}`: propios, sin `sancionatorio_alertas` (2) |
| M7 | sancionatoria | `GET /alerts/scheduler/status`: expone el estado interno del scheduler a cualquier usuario (1) |
| M8 | infraction | `POST/PUT/DELETE /actos/administrativos`, `/actos/comunicaciones`, `/actos/notificaciones` (9) |
| M9 | infraction | Escrituras de etapas: `POST /etapas/cierre`, `POST/PUT /etapas/concepto`, `POST/PUT /etapas/oficio-remite`, `POST/PUT/DELETE /etapas/solicitud-informacion`, `POST /etapas/informe-tecnico/.../crear`, `POST/PUT /etapas/respuesta`, `POST/PUT /etapas/medidas` (13) |
| M10 | infraction | `PUT /expedientes/{id}/datos-basicos`, `PATCH /expedientes/{id}/archivar` (2) |
| M11 | infraction | `POST/DELETE /involucrados/vinculos`: además devuelve 404 en lugar de 403 (2) |
| M12 | infraction | `GET /expedientes/alertas/todas`, `/alertas/{id}`: propios, sin `infraccion_alertas` (2) |

**Inconsistencias y otros:**

| # | Endpoint | Problema | Propuesta | Riesgo |
|---|---|---|---|---|
| M13 | `DELETE /users/notification/linked/{linked_id}` | Cualquier usuario borra las notificaciones **de todos los usuarios** con ese `id_vinculada`. No lo usa el frontend. | Restringirlo a `Notificacion.usuario_id == user_id`, o pasarlo a service-token | Ninguno |
| M14 | `GET /users/user/all` | Exige `admin_registrar_usuarios`, pero la pantalla `/user/manage` exige `admin_gestionar_usuarios`. Un rol que solo gestiona usuarios recibe 403 y ve la pantalla vacía. | Aceptar `admin_gestionar_usuarios` o `admin_registrar_usuarios` | Hoy **bloquea** a roles que solo tienen gestionar |
| M15 | `GET /users/role/all` | Exige `admin_roles_y_permisos`, pero lo usan `/user/manage` (selector de rol) y el modal de auditoría (`useAuditMappings`). | Aceptar también `admin_gestionar_usuarios`, `admin_registrar_usuarios` y `auditoria_*` en modo solo lectura | Hoy **bloquea** a los auditores y a quienes gestionan usuarios sin permiso de roles |
| M16 | `POST /documents/files/upload` | El backend **no valida nada**, ni siquiera `verify_gateway_token`. Solo lo protege la sesión del gateway. Si el puerto 8003 se expusiera (por ejemplo en `deploy/`), la subida sería anónima. | `verify_gateway_token`, más al menos un permiso de escritura de cualquier módulo | Ninguno |
| M17 | `GET /documents/files/{file_id}` | Igual que C1, pero solo con metadatos (`file_url` interna de MinIO, tamaño, usos). | Lo mismo que C1 | Bajo |
| M18 | api-gateway `PUBLIC_ROUTES` | Publica rutas que son solo de servicio: `users: role/verify, user/batch, user/permission, notification/add, email/*`, `documents: files/increment-usage, decrement-usage, batch`. Los backends exigen service-token, así que hoy **no se pueden explotar**, pero los servicios se llaman directamente (`UsersClient`/`FilesClient`) y no necesitan pasar por el gateway. Es superficie de ataque innecesaria. | Quitarlas de `PUBLIC_ROUTES`, o bloquearlas en el gateway (403) | Hay que verificar que ningún servicio las llame a través del gateway (no se encontró ningún caso) |
| — | Constante `VERIFY_PERMISSION: "/users/role/permission/verify"` en el frontend | La ruta no existe en el backend (la real es `/role/verify`, y es de servicio). Es código muerto. | Borrarla | — |
| — | Roles en el JWT | app-users obtiene los permisos a partir del `rol_id` del token. Si a alguien le cambian el rol, conserva los permisos del anterior hasta que vuelva a iniciar sesión. Los demás servicios usan `verify_permission(user_id)` con caché, así que el cambio llega con el TTL de la caché. | Invalidar la sesión en Redis al cambiar el rol de un usuario | — |

### OK (en resumen)

- **app-users:** auth (login, recovery, recovery-code, logout, me), los demás endpoints de rol y permiso (`admin_roles_y_permisos`, más la regla de no otorgar permisos que uno no tiene), `user/register` (registrar), `PATCH user/{id}` y `resend-password` (gestionar), `user/log` (auditoria_usuarios), autoservicio (`password-change`, `update-user`, notificaciones propias, `stream`), y los de servicio (`role/verify`, `user/batch`, `user/permission/*`, `notification/add`, `email/*`).
- **app-involved:** los 7 endpoints. `search` y `new` aceptan cualquier permiso de gestión (involucrado, sancionatorio o infracción); `manage`, `{id}` GET/PUT exigen `involucrado_gestionar`; `log` exige `auditoria_involucrados`; `bulk` es de servicio.
- **app-docs `/docs/*`:** `documento_crear`/`documento_revisar` más creador o revisor asignado. `download` y `download-revision` controlan solo la propiedad (creador o revisor del documento). Con eso basta: el conjunto de usuarios autorizados es exactamente ese. Los de `files/batch`, `increment`, `decrement` y `download-unified` son solo de servicio.
- **app-infraction:** `file_query.py` completo (tras la Tarea 1), `POST /expedientes` y `POST /denunciantes` (gestionar), `PATCH encargado` y `masivo` (asignar), `auditoria/registros`, `/informes/*` (asignar_informes, cargue, subir/revisar más asignación), `/revision-informes/*` (`FLUJO.puede_ver`: profesional, revisor o asignador), y los catálogos (`tipos-notificacion`, `tipos-medida`, `recursos-afectados`, `tipos-afectacion`, `municipios/veredas`).
- **app-sancionatoria:** `charge` y `charge/bulk` (asignar), `audit/logs` (auditoria_expedientes), catálogos (`affected-resource`, `measure-type`, `cessation-type`, `town/rural-district*`) y `stage/audit/batch` (solo etiquetas).
- **Sin token de gateway:** `POST /infraction/municipios/dias-habiles` y `POST /sanctioning/town/utils/business-days`. Son cálculo puro de fechas y no leen datos. Vía gateway exigen sesión porque no están en `PUBLIC_ROUTES`, y el frontend no los usa (la constante `BUSINESS_DAYS` no tiene consumidores). **OK.** Por coherencia se les puede añadir `verify_gateway_token`, o borrarlos.

### ¿Basta con el chequeo por propiedad?

- **Para escrituras sobre el expediente propio** (actos, etapas, datos básicos, archivar, vínculos), **casi basta**. La asignación ya está protegida por `*_asignar`, y solo se asigna a usuarios con `*_gestionar`. El hueco es la revocación: si a un abogado le quitan el permiso y no se reasignan sus expedientes, sigue escribiendo en ellos. Exigir además `*_gestionar` cuesta una consulta cacheada y no bloquea a nadie. Por eso se clasifican MEDIO y no OK.
- **Para lecturas no basta**, porque la mayoría no tiene ni siquiera chequeo de propiedad (`require_owner=False`, o ninguno). La regla correcta es la que ya aplica `/infraction/expedientes/completo`: **consultar ve todo; gestionar ve solo lo suyo.**
- **Documentos (app-docs `/docs/*`) y revisión de informes:** la propiedad (creador, revisor o profesional asignado) **sí basta**, porque esos son exactamente los actores del flujo y la asignación exige el permiso del rol.

---

## 4. Inventario por servicio

Leyenda de auth: **GW** = `verify_gateway_token`; **SVC** = service-token estricto; **PUB** = en `PUBLIC_ROUTES` del gateway; **—** = el backend no valida nada (depende de la sesión del gateway).

### 4.1 api-gateway

| Ruta | Auth | Nota | Sev. |
|---|---|---|---|
| `ANY /{service}/{path}` | sesión (cookie JWE + Redis), salvo `PUBLIC_ROUTES` | No controla permisos. Quita las cabeceras de confianza que manda el cliente. Bloquea traversal. Rate limit por IP y por usuario. | OK (por diseño) |
| `GET /health` | pública | | OK |
| `PUBLIC_ROUTES` | | Ver M18 | MEDIO |

### 4.2 app-users (`/users`)

| Método y ruta | Auth | Permiso en backend | Pantalla (permiso) | Sev. |
|---|---|---|---|---|
| POST /auth/login | PUB | — | login | OK |
| POST /auth/recovery | PUB | — | recover | OK |
| POST /auth/recovery-code | PUB | — | recover | OK |
| GET /auth/me | GW | propio | todas | OK |
| POST /auth/logout | PUB | cookie propia | header | OK |
| POST /email/send, /send-bulk, /send-alert-report | PUB+SVC | servicio | — | OK |
| POST /notification/add | PUB+SVC | servicio | — | OK |
| DELETE /notification/delete-all | GW | propias | header | OK |
| DELETE /notification/{id} | GW | propia | header | OK |
| DELETE /notification/linked/{linked_id} | GW | **ninguno (borra las de otros)** | sin uso | **MEDIO (M13)** |
| GET /notification/stream | GW | propias | header | OK |
| GET /role/all | GW | admin_roles_y_permisos | /user/role, **/user/manage, modal de auditoría** | **MEDIO (M15)** |
| GET /role/permissions, /role/role-permissions | GW | admin_roles_y_permisos | /user/role, modal de auditoría | OK (el modal sufre M15) |
| POST /role/add, PUT /role/update/{id}, DELETE /role/delete/{id} | GW | admin_roles_y_permisos + no escalar | /user/role | OK |
| POST/PUT/DELETE /role/permission/* | GW | admin_roles_y_permisos + no escalar | /user/role | OK |
| POST /role/verify | PUB+SVC | servicio | — | OK |
| GET /user/log | GW | auditoria_usuarios | /audit/users | OK |
| POST /user/register | GW | admin_registrar_usuarios + no escalar | /user/add | OK |
| GET /user/all | GW | admin_registrar_usuarios | **/user/manage (admin_gestionar_usuarios)** | **MEDIO (M14)** |
| PATCH /user/{id} | GW | admin_gestionar_usuarios + no escalar | /user/manage | OK |
| POST /user/resend-password/{id} | GW | admin_gestionar_usuarios | /user/manage | OK |
| POST /user/batch | PUB+SVC | servicio | — | OK |
| GET /user/permission/{name} | PUB+SVC | servicio | — | OK |
| POST /user/password-change, PUT /user/update-user | GW | propio | /profile | OK |

### 4.3 app-sancionatoria (`/sanctioning`)

Permisos de la pantalla: gestión `sancionatorio_gestionar`, consulta `sancionatorio_consultar`, asignación `sancionatorio_asignar`, alertas `sancionatorio_alertas`, auditoría `auditoria_expedientes`. En el backend solo existen las constantes `ASSIGN_PERMISSION`, `FILE_MANAGE` y `LOG_PERMISSION`, y **`FILE_MANAGE` solo se usa para listar usuarios, nunca para autorizar**.

| Método y ruta | Auth | Permiso en backend | Pantalla | Sev. |
|---|---|---|---|---|
| POST /expediente/add | GW | **ninguno** | /file/manage | **CRÍTICO (C2)** |
| GET /expediente/get | GW | **ninguno** | /file/assign_manage | **ALTO (A4)** |
| GET /expediente/get/all | GW | **ninguno** | /file/consult | **ALTO (A1)** |
| GET /expediente/full/{id} | GW | **ninguno** | — | **ALTO (A3)** |
| GET /expediente/{encargado_id} | GW | propio (403) | /file/manage | MEDIO (M5) |
| POST /expediente/filter | GW | propios | /file/manage | MEDIO (M5) |
| GET /expediente/affected-resource | GW | — (catálogo) | gestión/consulta | OK |
| PUT /expediente/{id}/basic-data | GW | encargado | /file/manage | MEDIO (M3) |
| PATCH /expediente/{id}/archive | GW | encargado | /file/manage | MEDIO (M3) |
| PATCH /expediente/{id}/charge/{enc} | GW | sancionatorio_asignar | /file/assign_manage | OK |
| PATCH /expediente/charge/bulk | GW | sancionatorio_asignar | /file/assign_manage | OK |
| GET /expediente/alerts/all, /alerts/{id} | GW | propios | /file/alerts | MEDIO (M6) |
| GET /expediente/audit/logs | GW | auditoria_expedientes | /audit/files | OK |
| GET /expediente/download-all/{id} | GW | **ninguno ("intencional")** | DetalleExpediente | **ALTO (A15)** |
| POST/PUT/DELETE /acto/acto-admin | GW | encargado | /file/manage | MEDIO (M1) |
| POST/PUT/DELETE /acto/communication | GW | encargado | /file/manage | MEDIO (M1) |
| POST/PUT/DELETE /acto/notificacion | GW | encargado | /file/manage | MEDIO (M1) |
| POST /alerts/send-weekly-report | GW | **ninguno** | — | **ALTO (A18)** |
| GET /alerts/scheduler/status | GW | ninguno | — | MEDIO (M7) |
| POST /involved/involved-file, DELETE /involved/involved-file/{id} | GW | encargado | /file/manage | MEDIO (M4) |
| GET /involved/involved-list/{exp} | GW | **ninguno** | InformacionExpediente | **ALTO (A16)** |
| GET /involved/file-list/{inv} | GW | **ninguno** | — | **ALTO (A17)** |
| GET /stage/{investigation…execution}/{id} (10) | GW | **solo que exista** | DetalleExpediente | **ALTO (A5–A14)** |
| POST/PUT /stage/{…}/{id} (15) | GW | encargado | /file/manage | MEDIO (M2) |
| GET /stage/measure-type, /stage/cessation-type | GW | — (catálogo) | | OK |
| GET /stage/full/{id} | GW | **ninguno** | DetalleExpediente | **ALTO (A2)** |
| POST /stage/doc-attached/{etapa} | GW | **ninguno** | /file/manage | **CRÍTICO (C3)** |
| PUT /stage/doc-attached/{etapa}/{doc} | GW | **ninguno** | /file/manage | **CRÍTICO (C4)** |
| DELETE /stage/doc-attached/{etapa}/{doc} | GW | **ninguno** | /file/manage | **CRÍTICO (C5)** |
| POST /stage/audit/batch | GW | — (etiquetas) | auditoría | OK |
| GET /town/rural-district, /rural-district/{id} | GW | — (catálogo) | | OK |
| POST /town/utils/business-days | — | — (cálculo) | sin uso | OK |

### 4.4 app-infraction (`/infraction`)

| Método y ruta | Auth | Permiso en backend | Pantalla | Sev. |
|---|---|---|---|---|
| GET /expedientes | GW | **infraccion_asignar** *(nuevo)* | /infraction/assign_manage | OK (antes ALTO) |
| GET /expedientes/todos | GW | **infraccion_consultar** *(nuevo)* | /infraction/consult | OK (antes ALTO) |
| GET /expedientes/encargado/{id} | GW | propio (**403**, antes 400) + **infraccion_gestionar** *(nuevo)* | /infraction/manage | OK (antes MEDIO) |
| GET /expedientes/completo/{id} | GW | **consultar, o gestionar + encargado** *(nuevo)* | DetalleInfraccion | OK (antes ALTO) |
| GET /expedientes/denunciantes | GW | **consultar, gestionar o auditoria_infracciones** *(nuevo)* | catálogos de consulta y gestión, /audit/infractions | OK (antes ALTO: teléfono y correo de quejosos) |
| POST /expedientes/filtrar | GW | "todos" con consultar; "propios" con **gestionar** *(nuevo)* | consulta y gestión | OK (antes MEDIO) |
| GET /expedientes/recursos-afectados, /tipos-afectacion | GW | — (catálogo) | varias | OK |
| POST /expedientes | GW | infraccion_gestionar | /infraction/manage | OK |
| POST /expedientes/denunciantes | GW | infraccion_gestionar | /infraction/manage | OK |
| PUT /expedientes/{id}/datos-basicos | GW | encargado | /infraction/manage | MEDIO (M10) |
| PATCH /expedientes/{id}/encargado/{enc}, /encargado/masivo | GW | infraccion_asignar | /infraction/assign_manage | OK |
| PATCH /expedientes/{id}/archivar | GW | encargado | /infraction/manage | MEDIO (M10) |
| GET /expedientes/alertas/todas, /alertas/{id} | GW | propios | /infraction/alerts | MEDIO (M12) |
| GET /expedientes/auditoria/registros | GW | auditoria_infracciones | /audit/infractions | OK |
| GET /expedientes/descargar/{id} | GW | **ninguno** | DetalleInfraccion | **ALTO (A19)** |
| POST/PUT/DELETE /actos/administrativos | GW | encargado | /infraction/manage | MEDIO (M8) |
| POST/PUT/DELETE /actos/comunicaciones | GW | encargado | /infraction/manage | MEDIO (M8) |
| POST/PUT/DELETE /actos/notificaciones | GW | encargado | /infraction/manage | MEDIO (M8) |
| GET /actos/tipos-notificacion | GW | — (catálogo) | | OK |
| POST /involucrados/vinculos, DELETE /vinculos/{id} | GW | encargado | /infraction/manage | MEDIO (M11) |
| GET /involucrados/expediente/{id} | GW | **ninguno** | DetalleInfraccion | **ALTO (A20)** |
| GET /involucrados/{id}/expedientes | GW | **ninguno** | — | **ALTO (A21)** |
| GET /etapas/respuesta/{id} | GW | **ninguno** | DetalleInfraccion | **ALTO (A22)** |
| POST /etapas/respuesta/{id}, PUT /respuesta/{etapa} | GW | encargado | /infraction/manage | MEDIO (M9) |
| POST/PUT /etapas/medidas/* | GW | encargado | /infraction/manage | MEDIO (M9) |
| GET /etapas/tipos-medida | GW | — (catálogo) | | OK |
| GET /etapas/informe-tecnico/{id}/{tipo} | GW | **solo que exista** | InformeTecnicoEtapa | **ALTO (A23)** |
| POST /etapas/informe-tecnico/{id}/crear/{tipo} | GW | encargado | /infraction/manage | MEDIO (M9) |
| GET /etapas/concepto/{id} | GW | **ninguno** | DetalleInfraccion | **ALTO (A24)** |
| POST/PUT /etapas/concepto, /oficio-remite, /solicitud-informacion (+DELETE) | GW | encargado | /infraction/manage | MEDIO (M9) |
| GET /etapas/cierre/{id} | GW | **ninguno** | DetalleInfraccion | **ALTO (A25)** |
| POST /etapas/cierre/{id} | GW | encargado | /infraction/manage | MEDIO (M9) |
| GET /etapas/migracion/medida/{radicado} | GW | **ninguno** | sancionatorio /file/manage | **ALTO (A26)** |
| GET /informes/disponibles | GW | infraccion_cargue | cargue manual | OK |
| GET /informes | GW | infraccion_asignar_informes | /infraction/reports | OK |
| POST/PUT /informes/{id}/asignar | GW | infraccion_asignar_informes | /infraction/reports | OK |
| PUT /informes/{id}/cambiar-modo, POST /cargue-manual | GW | infraccion_cargue | etapa Visita | OK |
| GET /informes/mios | GW | informes_subir \| informes_revisar | /infraction/my-reports | OK |
| GET/PUT /informes/{id}/recursos | GW | asignado, asignador o encargado / matriz | modales | OK |
| /revision-informes/* (6) | GW | `FLUJO.puede_ver` (profesional, revisor, asignador) | Mis informes | OK *(en edición por otro agente)* |
| GET /municipios/veredas, /veredas/{id} | GW | — (catálogo) | | OK |
| POST /municipios/dias-habiles | — | — (cálculo) | sin uso | OK |

### 4.5 app-docs (`/documents`)

| Método y ruta | Auth | Permiso en backend | Pantalla | Sev. |
|---|---|---|---|---|
| GET /docs/list | GW | documento_crear \| documento_revisar + propios o asignados | /document/manage | OK |
| GET /docs/detail/{id} | GW | crear \| revisar + creador o revisor | /document/manage | OK |
| POST /docs/create | GW | documento_crear (los revisores deben tener documento_revisar) | /document/manage | OK |
| POST /docs/upload-version/{id} | GW | documento_crear + creador | /document/manage | OK |
| POST /docs/review/{id} | GW | documento_revisar + asignado | /document/manage | OK |
| GET /docs/stats, /docs/reviewers | GW | crear \| revisar | /document/manage | OK |
| GET /docs/download/{ver}, /download-revision/{rev} | GW | creador o revisor (propiedad) | /document/manage | OK |
| POST /files/upload | **—** | **ninguno** | `shared/lib/fileUpload.ts` (todas las subidas) | MEDIO (M16) |
| GET /files/{id} | GW o SVC | **ninguno** | (sin uso en el frontend) | MEDIO (M17) |
| GET /files/download/{id} | GW o SVC | **ninguno** | `documentViewer.ts` (todos los visores) | **CRÍTICO (C1)** |
| POST /files/batch | PUB+SVC | servicio | — | OK |
| PUT /files/increment-usage, /decrement-usage | PUB+SVC | servicio | — | OK |
| POST /files/download-unified | SVC | servicio | — | OK |

### 4.6 app-involved (`/involveds`)

| Método y ruta | Auth | Permiso en backend | Pantalla | Sev. |
|---|---|---|---|---|
| GET /involved/search/{tipo}/{num} | GW (vía `_exigir_alguno`) | involucrado \| sancionatorio \| infraccion `_gestionar` | /involved/manage y vinculación desde gestión | OK |
| GET /involved/manage | GW | involucrado_gestionar | /involved/manage | OK |
| GET /involved/log | GW | auditoria_involucrados | /audit/involved | OK |
| POST /involved/bulk | SVC | servicio | — | OK |
| POST /involved/new | GW | cualquier `_gestionar` | gestión | OK |
| GET /involved/{id} | GW | involucrado_gestionar | /involved/manage | OK |
| PUT /involved/{id} | GW | involucrado_gestionar | /involved/manage | OK |

---

## 5. Plan sugerido (orden de ataque)

1. **C2–C5** (sancionatoria `add` y `doc-attached`): son cambios de una línea con un patrón que ya existe (`verify_permission` / `get_expediente_con_permiso`). No hay riesgo de bloqueo.
2. **C1** (descarga de archivos): primero, cuanto antes, exigir "cualquier permiso de módulo". Después diseñar URLs firmadas emitidas por el servicio dueño.
3. **Lecturas de expediente** (A1–A26): crear en cada servicio un helper `exigir_lectura_expediente(db, exp_id, user_id)` que aplique "consultar, o gestionar + encargado" (es lo que ya hace `/infraction/expedientes/completo`) y llamarlo desde `get_expediente_con_permiso(require_owner=False)` y desde los GET de etapas, involucrados y descargas. A26 debe aceptar también `sancionatorio_gestionar`.
4. **A18:** eliminar `send-weekly-report`, o pasarlo a service-token.
5. **MEDIO M1–M12:** añadir `*_gestionar` a `get_expediente_con_permiso(require_owner=True)` en ambos servicios. Es una sola función por servicio.
6. **M14/M15:** alinear app-users con las pantallas que consumen sus endpoints.
7. **M16–M18:** defensa en profundidad (`verify_gateway_token` en `files/upload`) y limpieza de `PUBLIC_ROUTES`.
8. Antes de cada despliegue, ejecutar la consulta de roles de la sección 1 en la VM.

## 6. Cambio aplicado en esta auditoría (Tarea 1)

`app-infraction/routes/file_query.py`. Helpers nuevos `_tiene_alguno` y `_exigir_alguno`, que usan `verify_permission` (app-users vía `UsersClient`):

| Endpoint | Antes | Ahora |
|---|---|---|
| `GET /expedientes` | solo token | `infraccion_asignar` |
| `GET /expedientes/todos` | solo token | `infraccion_consultar` |
| `GET /expedientes/encargado/{id}` | propio (400) | propio (**403**) + `infraccion_gestionar` |
| `GET /expedientes/completo/{id}` | solo token | `infraccion_consultar`, o `infraccion_gestionar` + encargado (403 si es ajeno o no existe, para no revelar qué IDs existen) |
| `GET /expedientes/denunciantes` | solo token | consultar \| gestionar \| auditoria_infracciones |
| `POST /expedientes/filtrar` | "propios" sin permiso | "propios" exige `infraccion_gestionar` |
| `recursos-afectados`, `tipos-afectacion` | solo token | sin cambio (catálogos) |

Tests: `app-infraction/tests/test_file_query_permissions.py` (23 casos, con y sin permiso). En `tests/test_file_filter.py` se ajustaron los fixtures porque el usuario de prueba ahora tiene `infraccion_gestionar`. Suite de infraction: **120 passed**. `docker compose up -d --build app-infraction`: **healthy**.

Riesgo de bloqueo: admin y sub admin (BD local) tienen consultar y gestionar. El rol de asignación solo usa `GET /expedientes`, y la auditoría solo `denunciantes`; ambos quedan cubiertos. **Hay que verificar los roles de la VM** con la consulta de la sección 1.
