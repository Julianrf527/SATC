# API de app-involved (Involucrados)

Catálogo único de personas naturales y jurídicas del SATC. Sancionatorio,
infracciones y recurso guardan solo el `involucrado_id` (sin llave foránea) y
piden los datos aquí.

El front llama con el prefijo del gateway **`/involveds`** (p. ej.
`GET /involveds/involved/manage`). El gateway reenvía a `app-involved:8004/{ruta}`
sin ese prefijo, así que todas las rutas de esta API empiezan por `/involved`.
Autenticación: cookie de sesión → el gateway inyecta `x-gateway-token`,
`X-Gateway-User-Id` y `X-Gateway-Role-Id`. Los otros microservicios llaman
directo (sin gateway) con `x-service-token` (ver `/bulk`).

Errores: `{"detail": "mensaje"}` con el código HTTP indicado.

## Reglas comunes

- **Permisos** (`core/permission.py`, catálogo en app-users). El permiso se
  valida **antes** de tocar la BD: sin permiso la respuesta es 403 exista o no
  el registro pedido.

  | Permiso | Pantalla | Qué habilita aquí |
  |---|---|---|
  | `involucrado_gestionar` | `/involved/manage` | Listar, ver, crear y editar involucrados |
  | `auditoria_involucrados` | `/audit/involved` | Log de auditoría |
  | `sancionatorio_gestionar`, `infraccion_gestionar`, `recurso_gestionar`, `recurso_super_gestion` | Formularios de vinculación de cada módulo | Solo **buscar** (`/search`) y **crear** (`/new`), para vincular desde el expediente |

- **Fail-closed**: si app-users no responde, el permiso se niega. Los permisos
  se cachean 5 min por worker.
- **Llave lógica**: `(numero_documento, tipo_documento)` es UNIQUE en la BD. El
  dígito de verificación **no** forma parte de la llave: no pueden existir dos
  NIT con el mismo número y distinto DV.
- **Dígito de verificación**: solo existe en NIT. Para cualquier otro tipo se
  guarda `null`, aunque el cliente lo mande.
- **Correo**: se guarda en minúsculas.
- **Auditoría**: alta y edición escriben un registro en la misma transacción;
  si la auditoría falla, la operación completa se cancela (500).

## Objeto involucrado

```json
{
  "id": 12,
  "numero_documento": 1098765432,
  "digito_verificacion": null,
  "tipo_documento": "CC",
  "nombre": "Nombre o razón social",
  "celular": 3001234567,
  "correo": "persona@dominio.co",
  "direccion": "Cra 5 # 10-20"
}
```

## Endpoints

### GET /involved/search/{tipo_documento}/{numero_documento}

Busca por documento. `?dv=` opcional (solo NIT): si se envía, también filtra
por DV.

- Permiso: cualquiera de la lista de vinculación (ver tabla).
- 200 `{"ok": true, "data": {involucrado}}`.
- 200 `{"ok": false, "data": null, "detail": "Involucrado no encontrado"}` si
  no existe (no es 404).
- 400 si el número no es numérico. 403 sin permiso.

### GET /involved/manage

Lista paginada. Query: `page` (≥1, def. 1), `limit` (1–100, def. 10),
`numero_documento` (igualdad; si no es numérico devuelve lista vacía),
`tipo_documento` (igualdad), `nombre` y `correo` (contiene, sin distinguir
mayúsculas). Orden: `id` descendente.

- Permiso: `involucrado_gestionar`.
- 200 `{"ok": true, "data": [...], "page", "limit", "totalCount"}`.

### GET /involved/{id}

- Permiso: `involucrado_gestionar`.
- 200 `{"ok": true, "data": {involucrado}}`. 404 si no existe. 422 si `id` ≤ 0.

### POST /involved/new

Body: `numero_documento` (int, 6–15 dígitos), `tipo_documento` (≤20),
`nombre` (1–100), y opcionales `digito_verificacion` (≤2), `celular` (int,
7–15 dígitos), `correo` (email), `direccion` (≤200).

- Permiso: cualquiera de la lista de vinculación.
- 201 `{"ok": true, "data": {involucrado}, "msg": ...}`.
- 409 si ya existe un involucrado con ese `(numero_documento, tipo_documento)`,
  tanto si lo detecta el chequeo previo como si dos altas concurrentes chocan
  en el UNIQUE.
- 422 datos inválidos.

### PUT /involved/{id}

**No es un PATCH**: `nombre` es obligatorio. El resto de campos (los mismos de
`/new`) son opcionales y **solo se modifican los que vienen en el body**; un
campo omitido conserva su valor. Mandar `null` en `celular`, `correo`,
`direccion` o `digito_verificacion` lo vacía.

- `numero_documento` y `tipo_documento` **no se pueden vaciar**: `null`
  explícito → 422.
- Si el tipo final no es NIT, el DV queda en `null` (p. ej. al pasar de NIT a CC).
- Permiso: `involucrado_gestionar`.
- 200 `{"ok": true, "data": {involucrado}, "msg": ...}`.
- 404 si no existe. 409 si el documento nuevo pertenece a otro involucrado
  (chequeo previo o choque concurrente en el UNIQUE). 422 datos inválidos.

### GET /involved/log

Log de auditoría. Query: `page`, `limit` (1–500), `offset` (tiene prioridad
sobre `page`), `usuario_id`, `tipo_evento`, `resultado`, `fecha_inicio` y
`fecha_fin` (`YYYY-MM-DD`; `fecha_fin` incluye todo el día), `nombre_usuario`
y `documento_usuario` (contiene).

- `nombre_usuario`/`documento_usuario` se resuelven contra app-users a la lista
  de autores que coinciden y se filtran en SQL: la paginación y el `total` son
  exactos. Si app-users no conoce a un autor, se busca sobre el texto que
  muestra la tabla (`"Usuario <id>"`).
- Orden: `fecha` descendente.
- Permiso: `auditoria_involucrados` (`involucrado_gestionar` no alcanza).
- 200 `{"ok": true, "data": [...], "msg", "pagination": {"page", "limit", "total", "pages"}}`.
  Cada fila trae `tipo_operacion`/`tabla_afectada` derivados de `tipo_evento`
  (`CREAR_INVOLUCRADO` → `INSERT`, `ACTUALIZAR_INVOLUCRADO` → `UPDATE`) y
  `datos_anteriores`/`datos_nuevos` sin el `id`.
- 400 fecha con formato inválido.

### POST /involved/bulk (solo servicio a servicio)

Body: `{"ids": [int, ...], "tipo_documento": "opcional"}` (`ids` no vacío).

- Exige `x-service-token` firmado con el secreto de `sanctioning-service`,
  `infraction-service` o `recurso-service`; la identidad la decide qué secreto
  valida la firma. El `x-gateway-token` **no** sirve aquí.
- Cliente: `satc_shared.clients.InvolvedClient.bulk(ids)`.
- 200 `{"ok": true, "data": [...], "total"}`. Los ids inexistentes se omiten
  sin error.
- 403 token ausente o inválido. 422 lista vacía.

### GET /health

Público. `{"status": "healthy", "service": "app-involved", "version": "1.0.0"}`.

## Pruebas

Ver el encabezado de `tests/conftest.py`: dependencias en
`requirements-dev.txt`, variables obligatorias y cómo se crea `involved_test_db`.
