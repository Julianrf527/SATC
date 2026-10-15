# Diseño técnico — app-recurso (Concesiones de Aguas)

Complementa `PLAN_CONCESIONES_AGUAS.md` (negocio) y `concesiones_dbml.txt` (modelo).
Este documento fija las decisiones **técnicas** comunes. Si algo de negocio no está en el plan → `TODO(negocio)` en el código, no inventar.

## 1. Identidad del servicio

| Cosa | Valor |
|---|---|
| Carpeta | `app-recurso/` |
| Servicio compose | `app-recurso`, puerto **8006** |
| BD | `recurso_db` en servicio `postgres-recurso` (contenedor `satc-postgres-recurso`), volumen `postgres-recurso-data` |
| BD de tests | `recurso_test_db` (mismo servidor) |
| Identidad este-oeste | `recurso-service`, secreto `RECURSO_SERVICE_SECRET` (app-users, app-docs y app-involved deben aceptarlo como caller) |
| Gateway | prefijo **`recurso`** → `http://app-recurso:8006` (`RECURSO_ROUTE`). El front llama `/recurso/<ruta del servicio>` |
| Rutas SPA | `/recurso/manage` (Gestionar), `/recurso/consult` (Consulta), `/recurso/my-reports` (Mis informes). nginx debe mandarlas al frontend como hace con `/infraction/(manage|…)` |
| Advisory lock init_db | 815123003 |
| Notificaciones app-users | `tipo = "recurso_doc"`, `id_vinculada = str(documento_proceso.id)` |

## 2. Ya hecho (base común — no rehacer)

- `db/models/*` (DBML nuevo + `version` para bloqueo optimista + modelos de revisión `documento_proceso*`), `db/database.py`, `db/deps.py`, `db/seeds.py`, `db/seed_data.py`.
- `core/permission.py` (slugs del plan §2), `core/acceso.py` (`requiere_permiso`, `requiere_lectura`, `requiere_gestion`, `Usuario.super_gestion`).
- `services/concurrencia.py` (`bloquear_expediente`, `actualizar_versionado`, `asignar_encargado`, `integridad_a_409`).
- `services/users.py`, `docs.py`, `involved.py`, `notification.py`, `utils/*` (copiados de infraction con identidad `recurso-service`).
- `main.py` con **todos** los routers ya registrados (stubs en `routes/*.py`). **No editar `main.py`**: cada agente llena sus módulos de `routes/`.

Desviación técnica del DBML: `concepto_tecnico.doc_concepto_tecnico_id` es **nullable** (la fila nace al seleccionar el técnico, antes de existir el concepto firmado, plan §4-E).

Desviación del DBML (14/10/2026): `encargado_acto_id` de `acto_admite`, `requerimiento` y `decision` admite **NULL** (el DBML lo pone `not null`). Motivo: el cargue directo de super gestión (§2.1) de expedientes antiguos puede dejar la etapa **sin abogado encargado** si no se elige uno. Se aplica con `ALTER COLUMN ... DROP NOT NULL` en `db/migrations.py`. El flujo normal no cambia: "Asignarme" siempre crea la fila con el encargado. Con encargado NULL: no se crea proceso de revisión (`_sincronizar_proceso`), el árbol no ofrece "Asignarme" sobre la fila existente (`nodo_acto(asignable=False)`), y el acto lo gestiona solo super gestión (`puede_gestionar_acto`, V2). `etapa_de_acto`, `leer_etapas` y mis-documentos toleran el NULL.

Columna añadida (14/10/2026): `comunicacion.fecha_creacion` (TIMESTAMPTZ, hora America/Bogota al crear; NULL en filas anteriores), mismo patrón que `acto_administrativo.fecha_creacion`.

## 3. Convenciones backend

- Patrón de rutas igual a infraction: `APIRouter`, `Depends(get_db_managed)`, el commit lo hace la ruta. Español en rutas/campos/mensajes. Body JSON (Pydantic) salvo cargue de archivos (`multipart`).
- Archivos: el **front** sube a app-docs (`/documents/files/...`, igual que infraction) y manda `file_id`. El backend registra uso con `services/docs.increment_file_usage` (y `decrement` al reemplazar/borrar). Verificar cómo lo hace infraction antes de escribir.
- Permisos: siempre `core/acceso.py`. Escritura = `requiere_gestion` (V1). Lectura = `requiere_lectura`. Revisor/técnico según §5.
- `super_gestion=True` omite validaciones de negocio §6, asignación y revisión. Nunca omite constraints de BD.
- Concurrencia (§7): transiciones críticas dentro de `bloquear_expediente`; ediciones con `version` del cliente → `actualizar_versionado`; creación de etapa → `integridad_a_409`. Toda respuesta de lectura de un registro editable incluye su `version`.
- Reglas de negocio **solo en backend**: cada payload de lectura de etapa trae `acciones_disponibles` (lista de códigos, p. ej. `["asignarme", "seleccionar_tecnico", "cargar_version_final", "crear_notificacion"]`) y/o motivos de bloqueo. El front no recalcula reglas.
- Auditoría: `utils/log.py` como infraction donde aplique.
- Tests: `pytest` + `pytest-asyncio` + httpx `ASGITransport` contra Postgres real (`TEST_DATABASE_URL`), aislamiento por TRUNCATE (copiar patrón de `app-infraction/tests/conftest.py`). Los servicios externos (users/docs/involved/notification) se mockean con `monkeypatch` en los wrappers de `services/`.
- Cada agente backend documenta sus endpoints en **`app-recurso/API.md`** (sección propia: método, ruta, permiso, body, respuesta, errores). El frontend se construye SOLO con lo que diga API.md.

## 4. Proceso de revisión de documentos (§5 del plan)

Modelo: `documento_proceso` (+ version/revision/auditoria/revisor) con los mixins de `satc_shared.review_process`. Un proceso por fila de etapa: `(etapa_tipo, etapa_ref_id)` = tabla e id de la fila; `tipo_documento` elige la cadena; `paso_actual` = índice del paso; `activo` = vigente.

**Cadenas** (`tipo_documento` → pasos; cada paso = conjunto de permisos que deben revisar **todos**, en cualquier orden):

| tipo_documento | etapa_tipo | Encargado (creador) | Pasos |
|---|---|---|---|
| `AUTO_ADMITE` | acto_admite | abogado `encargado_acto_id` | [{lider_juridico}], [{lider_proyecto}] |
| `REQUERIMIENTO` (etapa 3, memorias y obras) | requerimiento | abogado | [{lider_juridico}], [{lider_proyecto}] |
| `APRUEBA_MEMORIAS` | memorias_calculo | abogado | [{lider_juridico}], [{lider_proyecto}] |
| `DECISION` | decision | abogado | [{lider_juridico}], [{lider_proyecto, asesora_subdireccion}] |
| `RECURSO` | recurso_reposicion | abogado | [{lider_juridico}], [{lider_proyecto, asesora_subdireccion}] |
| `RECONOCE_TERCERO` | expediente_involucrado | abogado | `TODO(negocio)`: el plan no dice quién revisa. Provisional: igual que AUTO_ADMITE, configurable en un solo lugar |
| `APRUEBA_OBRAS` | recibo_satisfaccion_obras | abogado | `TODO(negocio)` (plan §4-Etapa 6). Provisional: igual que AUTO_ADMITE |
| `CONCEPTO_ETAPA2` | concepto_tecnico | técnico `tecnico_encargado_id` | [{lider_tecnico, sig}], [{lider_proyecto}] |
| `CONCEPTO_ADICIONAL` | concepto_tecnico | técnico | [{lider_tecnico}] |
| `CONCEPTO_MEMORIAS` / `CONCEPTO_SUBSANACION` / `CONCEPTO_OBRAS` / `CONCEPTO_OBRAS_SEGUNDO` | concepto_tecnico | técnico | [{lider_tecnico}] |

**Máquina de estados** (extiende `FlujoRevision`, como `FlujoInformeTecnico` de infraction):
`pendiente_carga → en_revision → (aprobado parcial: sigue en_revision / avanza paso) → aprobado_firma → [encargado sube firmada PDF] → aprobado`; `devuelto → rechazado → [nueva versión] → en_revision`.
1. Puede revisar quien tenga un permiso del paso actual **que aún no haya revisado en ese paso** (`documento_proceso_revision.paso/permiso`). Un usuario con dos permisos del paso revisa una vez por permiso.
2. Aprobar: registra (paso, permiso). Si todos los permisos del paso revisaron → si hay más pasos, `paso_actual += 1` (sigue `en_revision`); si era el último, estado `aprobado_firma` ("aprobado para firma").
3. Devolver (comentario obligatorio, adjunto opcional): registra (paso, permiso) y pasa a `rechazado`. Al subir la nueva versión vuelve a `en_revision` en el **mismo** paso; el permiso que devolvió ya cuenta como revisado (§5.2 "no revisa dos veces"), así que si era el último pendiente del paso avanza.
4. En `aprobado_firma` el encargado sube la versión firmada (solo PDF) → auto-aprobada (`aprobado`). Esta subida la hacen los **endpoints de cada etapa** ("cargar versión final"), que en la misma transacción crean el `acto_administrativo` / llenan los datos del concepto.
5. Sin límite de devoluciones: `max_devoluciones` muy alto + `TODO(negocio)` (el plan no define tope y no hay reasignación).
6. Para `puede_ver`: encargado, quien tenga algún permiso de revisor de la cadena, `recurso_consultar`/`recurso_gestionar`.
7. Notificaciones (best-effort tras commit, como `Avisos` de infraction) a los usuarios con el permiso del paso que queda pendiente y al encargado cuando devuelven / aprueban para firma.

**Mis informes**: por subir = procesos activos donde soy creador y estado ∈ {pendiente_carga, rechazado, aprobado_firma} + etapas donde soy encargado/técnico y aún no hay proceso; por revisar = procesos `en_revision` cuyo paso actual tiene un permiso que tengo y que no ha revisado.

## 5. Ciclo de vida de etapas (§4-E)

1. "Asignarme para diligenciar" crea la fila de la etapa con `encargado_acto_id = yo` (unique de la etapa → 409 si otro llegó antes) o, si la fila ya existe sin encargado (recurso, memorias, obras), `asignar_encargado` atómico. Al asignarse se crea el `documento_proceso` en `pendiente_carga`.
2. Proyección/revisión: endpoints genéricos `/revision-documentos/*`.
3. "Cargar versión final" (por etapa): PDF firmado + datos que vienen escritos en el documento (numerado, fecha de numerado; en auto admite además técnico + fecha de visita → nace etapa 2). Crea `acto_administrativo` y lo enlaza.
4. Notificación / comunicación: `/actos/*`.

## 6. Reparto de archivos (para no pisarse)

| Agente | Archivos propios |
|---|---|
| **A — base y expediente** | `routes/catalogos.py`, `routes/expediente_query.py`, `routes/expediente_mutations.py`, `routes/expediente_descarga.py`, `routes/involucrados.py`, `services/expediente*.py`, `tests/conftest.py`, `tests/test_expediente*.py`, `tests/test_involucrados.py`, infraestructura (`docker-compose.yml`, `api-gateway/main.py`, `nginx/nginx.conf`, `app-users` seeds/verify_token, `app-docs` y `app-involved` callers, `.env.example`), sección A de API.md |
| **B — revisión y actos** | `services/revision_documentos.py`, `routes/revision_documentos.py`, `routes/mis_documentos.py`, `routes/actos.py`, `services/actos.py`, `tests/test_revision*.py`, `tests/test_actos*.py`, sección B de API.md |
| **C — etapas** | `routes/etapa_*.py`, `routes/tercero_interviniente.py`, `routes/documentos_anexos.py`, `routes/super_gestion.py`, `services/etapas*.py`, `services/validaciones.py`, tests de etapas, sección C de API.md. Agrega a `GET /expedientes/{id}` el árbol de etapas vía un servicio propio que A expone como hook (`services/etapas_lectura.py`) |
| **F1/F2 — frontend** | `frontend/src/modules/app-recurso/**`, `frontend/src/shared/lib/api/endpoints/recurso.ts`, rutas en `frontend/src/app/App.tsx`. Features existentes (`@features/*`) se reutilizan **sin modificarlas**; si no encajan, se replica dentro del módulo |

## 7. Entorno local de verificación (esta máquina)

Docker/WSL no arranca en esta máquina. Hay un Postgres 15 local en el scratchpad de la sesión:

- Host `127.0.0.1`, puerto `55432`, usuario `postgres`, clave `Satc2026#Secure`. BDs: `recurso_test_db`, `recurso_db`.
- Correr tests: `cd app-recurso && TEST_DATABASE_URL='postgresql+asyncpg://postgres:Satc2026%23Secure@127.0.0.1:55432/recurso_test_db' ../.venv/Scripts/python.exe -m pytest -q`
- El default de `TEST_DATABASE_URL` en `conftest.py` sigue apuntando a `postgres-recurso:5432` (Docker), como los demás servicios.
- Node portable para el frontend: `/c/Users/julia/AppData/Local/Temp/claude/c--Users-julia-Escritorio-SATC/55e567c5-80ff-45c2-9776-85db605c9193/scratchpad/node-v22.11.0-win-x64` (agregar al PATH; usar `npm.cmd`/`npx.cmd`).
