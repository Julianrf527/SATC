# API de app-infraction (Infracciones ambientales)

El front llama todo con el prefijo del gateway **`/infraction`** (p. ej.
`GET /infraction/expedientes/todos`). El gateway reenvía a
`app-infraction:8005/{ruta}` sin el prefijo. Autenticación: cookie de sesión →
el gateway inyecta `x-gateway-token`, `X-Gateway-User-Id`, `X-Gateway-Role-Id`.
Errores: `{"detail": "mensaje"}` con el código HTTP indicado.

Índice:

- **A — Expedientes**: catálogos, consulta, alta/edición, encargado, archivo,
  involucrados, alertas, descarga y auditoría.
- **B — Etapas**: respuesta (+ medida preventiva), informe técnico de visita,
  acoger concepto (+ oficio remite / solicitud de información), informe de
  seguimiento y cierre.
- **C — Actos administrativos**: acto, notificación y comunicación (comunes a
  medida preventiva, concepto y cierre), proceso de revisión del acto
  (`/revision-actos`) y Mis actuaciones (`/mis-actuaciones`).
- **D — Informes técnicos**: asignación, cargue manual, listado de los míos, matriz de
  recursos afectados y proceso de revisión (`/revision-informes`).

Los procesos de revisión de informes y de actos viven en **una sola familia de
tablas** (`documento_proceso`, `_version`, `_revision`, `_auditoria`,
`_revisor`), como en app-recurso: `etapa_tipo` + `etapa_ref_id` dicen de qué
fila de etapa es cada proceso (`informe_tecnico`, `medida_preventiva`,
`etapa_concepto`, `etapa_cierre`) y `tipo_documento` qué documento es
(`INFORME_VISITA`, `INFORME_SEGUIMIENTO`, `ACTO_MEDIDA`, `ACTO_CONCEPTO`,
`ACTO_CIERRE`). A lo sumo un proceso **vigente** (`activo`) por etapa.

## Reglas comunes

- **Respuestas**: casi todas son `{"ok": true, ...}`; la forma exacta del
  resto del cuerpo varía por endpoint (`data`, `message`, campos sueltos) y se
  documenta en cada uno. No hay sobre común.
- **Permisos** (`core/permission.py`, catálogo en app-users):

  | Permiso | Pantalla | Qué habilita aquí |
  |---|---|---|
  | `infraccion_consultar` | `/infraction/consult` | Leer **cualquier** expediente (solo lectura) y descargarlo |
  | `infraccion_gestionar` | `/infraction/manage` | Crear expedientes; leer **solo los suyos**. Ser elegible como abogado responsable |
  | `infraccion_asignar` | `/infraction/assign_manage` | Listado global + cambiar el abogado responsable |
  | `infraccion_alertas` | `/infraction/alerts` | Alertas de **todos** los expedientes (`alcance=todos`) |
  | `infraccion_asignar_informes` | `/infraction/reports` | Asignar técnico (profesional) y líder técnico (revisor) a los informes técnicos |
  | `infraccion_tecnico` | `/infraction/my-reports` (Mis actuaciones) | Ser técnico (antes `infraccion_informes_subir`): subir versiones, cargar la versión final firmada con la matriz y editar la matriz |
  | `infraccion_lider_tecnico` | `/infraction/my-reports` (Mis actuaciones) | Ser líder técnico (antes `infraccion_informes_revisar`): aprobar para firma / devolver informes |
  | `infraccion_lider_proyecto` | `/infraction/my-reports` (Mis actuaciones) | Revisar los actos administrativos (medida preventiva, acoger concepto, cierre): aprobar para firma / devolver. Por permiso, sin asignación |
  | `infraccion_super_gestion` | — | Cargue manual de informes (histórico) y cambio de modo FLUJO/MANUAL; **cargue directo** de actos (sin revisión), cambiar el PDF de un acto y eliminar actos |
  | `auditoria_infracciones` | `/audit/infractions` | Logs de auditoría |

  Todos los de infracciones (salvo `gestionar`) exigen `infraccion_consultar`
  en el mismo rol; `super_gestion` exige `gestionar`. `infraccion_tecnico` es
  **incompatible** con `infraccion_gestionar` en el mismo rol (como
  `recurso_tecnico`), y por tanto también con `super_gestion`. Los renombres
  los aplica app-users al arrancar (`RENOMBRES`): los roles conservan el permiso.
- **Regla de lectura de un expediente** (`services/etapas.exigir_lectura_expediente`):
  `infraccion_consultar` ve cualquiera; `infraccion_gestionar` solo los que
  tiene a cargo (`abogado_responsable_id == usuario`). Si no existe o no lo
  puede ver → `403 "Sin permisos sobre este expediente"` (nunca 404, para no
  revelar qué IDs existen).
- **Regla de escritura**: todas las escrituras de un expediente (datos
  básicos, etapas, actos, involucrados, archivar) exigen ser el **abogado
  responsable** del expediente. Excepción, los actos administrativos (C): el
  encargado los proyecta por el proceso de revisión y solo super gestión los
  carga directo, cambia su PDF o los elimina. No se valida un permiso adicional: ser el
  encargado ya implica `infraccion_gestionar` (se valida al asignarlo).
- **Archivos**: el front sube el archivo a app-docs (`/documents/files/upload`)
  y envía aquí solo el `file_id`. El backend suma/resta el uso del archivo en
  app-docs (`numero_usos`); si un archivo queda en 0 usos la limpieza nocturna
  de app-docs lo borra. Los documentos que se unen al PDF del expediente
  (radicado inicial, informe técnico) deben ser PDF.
- **Auditoría**: toda escritura deja un registro en `auditoria` en la misma
  transacción; si no se puede guardar → `500 "Error al guardar registro de
  auditoría"` y no se guarda nada.
- **Formato de fechas**: `YYYY-MM-DD` (fechas) e ISO 8601 (timestamps,
  zona `America/Bogota`).
- **Sin bloqueo optimista**: a diferencia de app-recurso no hay `version`; la
  última escritura gana.
- `GET /health` (sin prefijo ni auth) → `{"status": "healthy", "service": "app-infracciones", "version": "1.0.0"}`.

---

## A — Expedientes

### A.1 Catálogos (solo token del gateway, sin permiso)

| Método | Ruta | Respuesta |
|---|---|---|
| GET | `/infraction/municipios/veredas` | `{"ok": true, "data": [{id, nombre, veredas: [{id, nombre}]}]}` (orden por nombre) |
| GET | `/infraction/municipios/veredas/{municipio_id}` | `{"ok": true, "veredas": [{id, nombre}]}` |
| GET | `/infraction/expedientes/recursos-afectados` | `{"ok": true, "data": [{id, nombre}]}` |
| GET | `/infraction/expedientes/tipos-afectacion` | `{"ok": true, "data": [{id, nombre, recurso_id}]}` |
| GET | `/infraction/etapas/tipos-medida` | `{"ok": true, "data": [{id, nombre}]}` |
| GET | `/infraction/actos/tipos-notificacion` | `{"ok": true, "data": [{id, nombre}]}` |

### A.2 Quejosos (denunciantes)

#### `GET /infraction/expedientes/denunciantes`

Permiso: `infraccion_consultar`, `infraccion_gestionar` o
`auditoria_infracciones` (trae datos personales).

```json
{"ok": true, "data": [{"id": 4, "nombre": "Ana Pérez", "telefono": "3001234567", "correo": "ana@x.co", "anonimo": false}]}
```

#### `POST /infraction/expedientes/denunciantes` (`infraccion_gestionar`)

Body `{nombre?, telefono?, correo?, anonimo: false}`.

- `anonimo: true` → se crea sin datos (se ignoran los demás campos).
- Si no es anónimo: `nombre` obligatorio y no puede aludir a "anónimo";
  `telefono` solo dígitos, ≤ 10; `correo` con formato válido. Si no → `400`.

Respuesta `201`: `{"ok": true, "data": {id, nombre, telefono, correo, anonimo}}`.

### A.3 Listados de expedientes

Los tres listados de abajo devuelven ítems con **la misma forma**:

```json
{
  "id": 12,
  "radicado": "2026ER00045",
  "fecha_radicado": "2026-02-10",
  "fecha_creacion": "2026-02-11T09:30:00-05:00",
  "archivado": false,
  "municipio": {"id": 3, "nombre": "Tunja"},
  "involucrados": [{"id": 20, "tipo_documento": "CC", "numero_documento": 1020304050, "nombre": "Pedro Gómez", "...": "..."}],
  "etapa_actual": "visita",
  "estado": "VISITA PROGRAMADA"
}
```

- `involucrados`: datos de app-involved. Si app-involved no responde, llega `[]`.
- `etapa_actual`: la etapa **más avanzada** que existe (no la más reciente):
  `respuesta` < `visita` < `concepto` < `seguimiento` < `cierre`, o `null`.
- `estado`: indicador de gestión (primera regla que se cumpla, o `null`):

  | Estado | Cuándo |
  |---|---|
  | `ARCHIVADO` | `archivado = true` |
  | `NOTIFICAR Y/O COMUNICAR ACTO ADM DE SEGUIMIENTO` | Hay cierre con acto y nadie ha sido notificado con éxito |
  | `PARA PROGRAMAR SEGUIMIENTO` / `SEGUIMIENTO PROGRAMADO` | Existe informe de seguimiento, sin / con fecha de visita |
  | `VISITA DE SGTO A CUMPLIMIENTO` | Concepto `AUTO_REQUERIMIENTO` con acto notificado |
  | `NOTIFICAR Y/O COMUNICAR ACTO ADM. ARCHIVADO` | Concepto `AUTO_REQUERIMIENTO` con acto sin notificar |
  | `POR ALLEGAR INFORMACIÓN` | Concepto con solicitud de información y sin involucrados |
  | `PARA PROGRAMAR VISITA` | Informe de visita sin fecha de programación |
  | `ACOGER CONCEPTO` | Informe de visita aceptado y sin concepto |
  | `VISITA PROGRAMADA` | Informe de visita programado |

#### `GET /infraction/expedientes/todos` (`infraccion_consultar`)

Todos los expedientes (vista Consulta). `{"ok": true, "data": [...]}`. Sin paginación.

#### `GET /infraction/expedientes/encargado/{encargado_id}` (`infraccion_gestionar`)

Expedientes del usuario (vista Gestionar). `encargado_id` debe ser el propio
usuario; otro id → `403`. `{"ok": true, "data": [...]}`.

#### `POST /infraction/expedientes/filtrar`

Filtrado avanzado. Body (`FiltroAvanzado`, todo opcional):

| Campo | Tipo | Filtro |
|---|---|---|
| `direccion` | str | contiene (sin mayúsculas); igualdad exacta si `valor_exacto` |
| `valor_exacto` | bool (default `false`) | |
| `municipio_id` | int | municipio de la vereda |
| `vereda_ids` | int[] | |
| `recurso_ids` | int[] | tiene **alguno** de los recursos |
| `tipo_afectacion_ids` | int[] | tiene **alguno** de los tipos |
| `alcance` | `"propios"` (default) \| `"todos"` | |

Los filtros se combinan con AND. `alcance="todos"` solo aplica si el usuario
tiene `infraccion_consultar`; si no, cae a `"propios"`, que exige
`infraccion_gestionar` (sin ninguno → `403`). Respuesta `{"ok": true, "data": [...]}`.

#### `GET /infraction/expedientes` (`infraccion_asignar`)

Listado paginado para la pantalla de asignación. Query params:

| Param | Tipo | Filtro |
|---|---|---|
| `page` | int ≥ 1 (default 1) | |
| `limit` | int 1–200 (default 10) | |
| `radicado` | str | contiene |
| `fecha_creacion` | ISO date | día de creación |
| `encargado_id` | int | |

Orden: más recientes primero.

```json
{
  "ok": true,
  "data": [{
    "id": 12, "radicado": "2026ER00045", "fecha_radicado": "2026-02-10",
    "encargado_id": 7, "encargado_nombre": "Laura Díaz", "encargado_documento": "1012345678",
    "fecha_creacion": "2026-02-11T09:30:00-05:00", "archivado": false, "estado": null
  }],
  "usuarios_disponibles": [{"id": 7, "nombre": "Laura Díaz", "numero_documento": "1012345678"}],
  "page": 1, "limit": 10, "totalCount": 1
}
```

`usuarios_disponibles`: usuarios con `infraccion_gestionar` (los que se pueden
asignar).

### A.4 Detalle del expediente

#### `GET /infraction/expedientes/completo/{expediente_id}` (lectura)

```json
{
  "ok": true,
  "data": {
    "id": 12,
    "radicado": "2026ER00045", "fecha_radicado": "2026-02-10",
    "fecha_creacion": "2026-02-11T09:30:00-05:00",
    "municipio": {"id": 3, "nombre": "Tunja"},
    "vereda": {"id": 9, "nombre": "Runta"},
    "direccion": "Km 3 vía Tunja", "descripcion": "Tala de bosque nativo",
    "recurso_afectado": [{"id": 1, "nombre": "FLORA"}],
    "tipos_afectacion": [{"id": 2, "nombre": "Tala", "recurso_id": 1}],
    "quejosos": [{"id": 4, "nombre": "Ana Pérez", "anonimo": false}],
    "radicados_asociados": ["2026ER00050"],
    "involucrados": [{"id": 20, "nombre": "Pedro Gómez", "...": "..."}],
    "etapa_actual": "respuesta",
    "ultima_etapa": "respuesta",
    "archivado": false,
    "estado": null,
    "radicado_inicial": {"file_id": 101, "nombre": "Radicado inicial"}
  },
  "etapas_existentes": [1]
}
```

- `ultima_etapa`: igual a `etapa_actual` (se conserva por compatibilidad).
- `radicado_inicial`: `null` si no se ha cargado.
- `etapas_existentes`: ids numéricos de las etapas creadas (los del
  `tabToEtapaMap` del front): `1` respuesta, `2` visita, `3` concepto,
  `4` seguimiento, `5` cierre.

Errores: `403`, `404` (solo si tiene `infraccion_consultar` y no existe).

### A.5 Crear y editar

Body común (`ExpedienteSchema`):

| Campo | Tipo | Regla |
|---|---|---|
| `radicado` | str | único |
| `fecha_radicado` | date | |
| `vereda_id` | int | |
| `abogado_responsable_id` | int \| null | solo al crear (ver abajo); se ignora al editar |
| `direccion` | str | |
| `descripcion` | str | |
| `tipos_afectacion_ids` | int[] | |
| `quejosos_ids` | int[] | ids de A.2 |
| `recursos_ids` | int[] | |
| `radicados_asociados` | str[] | se recortan, pasan a MAYÚSCULAS y se quitan vacíos y repetidos |
| `radicado_inicial_file_id` | int \| null | solo al crear; PDF ya subido a app-docs |

#### `POST /infraction/expedientes` (`infraccion_gestionar`)

- `abogado_responsable_id`: la pantalla envía al propio usuario; si es otro,
  debe tener `infraccion_gestionar` (si no → `400`).
- `radicado` repetido → `400 "El radicado ya existe"`.
- `radicado_inicial_file_id` inexistente o no PDF → `400`. Si no se puede
  registrar su uso en app-docs → `502` y no se crea.

Respuesta `200`: `{"ok": true, "expediente_id": 12}`.

#### `PUT /infraction/expedientes/{expediente_id}/datos-basicos` (encargado)

Reemplaza datos y **todas** las relaciones (quejosos, recursos, tipos,
radicados asociados) por las del body. No cambia el encargado ni el radicado
inicial. Radicado ya usado por otro expediente → `409`.

Respuesta: `{"ok": true, "message": "Expediente actualizado exitosamente", "expediente_id": 12, "radicado": "..."}`.
Errores: `403`, `404`, `409`, `422`.

#### `PUT /infraction/expedientes/{expediente_id}/radicado-inicial` (encargado + `infraccion_gestionar`)

Body `{"file_id": 101}` (PDF ya subido). Adjunta o reemplaza: +1 uso al nuevo
y −1 al anterior. Mismo `file_id` que el actual → `200` sin cambios.

Respuesta: `{"ok": true, "message": "Radicado inicial adjuntado" | "Radicado inicial actualizado", "file_id": 101}`.
Errores: `400` (no existe / no es PDF), `403`, `502` (no se pudo registrar el uso).

### A.6 Abogado responsable (encargado) — `infraccion_asignar`

#### `PATCH /infraction/expedientes/{expediente_id}/encargado/{encargado_id}`

`encargado_id = 0` quita el encargado. El nuevo encargado debe tener
`infraccion_gestionar` (si no → `400`). Al asignar se envía una notificación
in-app al encargado (`tipo = "exp_infraccion"`, `id_vinculada` = radicado) y,
por cada acto con proceso de revisión **en curso** en el expediente, otra
(`tipo = "acto_infraccion"`) avisando que ahora le toca continuarlo: los
procesos de acto siguen al encargado actual (C.4).

Respuesta: `{"ok": true, "message": "Encargado actualizado"}`. Errores: `400`, `403`, `404`.

#### `PATCH /infraction/expedientes/encargado/masivo`

Body `{"expediente_id": [1, 2, 3], "encargado_id": 7}` (`0` = quitar). Los ids
que no existan se ignoran. Una notificación por expediente al nuevo encargado
(y el aviso de actos en proceso, como en el PATCH individual).

```json
{"ok": true, "updated": [{"id": 1, "radicado": "2026ER00001"}], "msg": "Se actualizaron 1 expedientes"}
```

Errores: `400` (lista vacía o encargado sin permiso), `403`.

### A.7 Archivar — `PATCH /infraction/expedientes/{expediente_id}/archivar` (encargado)

Irreversible. Ya archivado → `400`. Respuesta: `{"ok": true, "message": "Expediente archivado exitosamente"}`.
Errores: `400`, `403`, `404`.

### A.8 Involucrados — `/infraction/involucrados`

Las personas viven en app-involved; aquí solo el vínculo
expediente ↔ `involucrado_id`. Para buscar o crear la persona se usa
app-involved (`/involved/...`) y luego se vincula aquí.

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| GET | `/involucrados/expediente/{expediente_id}` | lectura | `{"ok": true, "data": {"expediente_id", "involucrados": [persona de app-involved]}}` (`[]` si app-involved no responde) |
| POST | `/involucrados/vinculos` | encargado | Body `{expediente_id, involucrado_id}`. Ya vinculado → `400`; expediente ajeno o persona inexistente → `404` |
| DELETE | `/involucrados/vinculos/{involucrado_id}?expediente_id=N` | encargado | Desvincula y **borra sus notificaciones** en los actos del expediente (medida, concepto, cierre). Sin vínculo → `404` |
| GET | `/involucrados/{involved_id}/expedientes` | `infraccion_consultar` o `involucrado_gestionar` | `{"ok": true, "data": {"expedientes": [{id, radicado, fecha_radicado, fecha_creacion}], "total"}}`. Sin expedientes → `404` |

Respuestas de escritura: `{"ok": true, "data": {"message": "..."}}` (el POST
también devuelve `involucrado_id` y `expediente_id`).

### A.9 Alertas de vencimiento

Cada alerta:

```json
{
  "tipo": "respuesta_plazo",
  "etapa": "Respuesta",
  "accion_requerida": "Registrar la etapa de respuesta con radicado y fecha de radicado",
  "plazo_legal": "15 días hábiles desde la creación del expediente",
  "msg": "...",
  "fecha_inicio": "2026-02-11", "fecha_limite": "2026-03-04",
  "semaforo": {
    "estado": "amarillo", "color_hex": "#f59e0b", "porcentaje_avance": 61.9,
    "urgencia": "media", "dias_transcurridos": 13, "dias_restantes": 8,
    "dias_totales": 21, "esta_vencido": false
  }
}
```

Reglas (días hábiles con festivos de Colombia):

| `tipo` (clave) | Cuándo | Plazo |
|---|---|---|
| `respuesta_plazo` | No existe la etapa respuesta | 15 días hábiles desde la creación del expediente |
| `concepto_constancia` (`concepto_constancia_{notif_id}`) | Concepto `AUTO_REQUERIMIENTO` con acto; por cada notificación con constancia de citación y `notificacion_exitosa = false` | 15 días hábiles desde la constancia (si no se notifica, pasar a comunicación) |
| `concepto_termino` | Concepto con `dias_termino` calculado | Vence en `fecha_termino_calculada` |

Semáforo: `verde` < 50 % < `amarillo` < 80 % ≤ `rojo`; pasada la fecha límite, `vencido`.

#### `GET /infraction/expedientes/alertas/todas`

| Param | Tipo | |
|---|---|---|
| `alcance` | `mios` (default) \| `todos` | `todos` exige `infraccion_alertas` |
| `page` | int ≥ 1 | si llega, respuesta paginada |
| `limit` | int 1–100 (default 10) | |
| `radicado` | str | contiene (solo con `page`) |
| `estado` | `verde` \| `amarillo` \| `rojo` \| `vencido` | solo con `page` |
| `tipo` | str | solo con `page` |

Cada alerta trae además `es_responsable` (el usuario es el encargado) para
enlazar a Gestionar o a Consulta.

Sin `page` (forma anterior, ignora filtros):

```json
{
  "ok": true, "alcance": "mios",
  "alertas": {"2026ER00045": {"respuesta_plazo": {"...": "..."}}},
  "total_expedientes": 3, "expedientes_con_alertas": 1,
  "estadisticas_semaforo": {"verde": 0, "amarillo": 1, "rojo": 0, "vencido": 0}
}
```

Con `page`: lista plana ordenada por urgencia y % de avance; cada ítem lleva
además `radicado` y `clave`. Campos: `alertas`, `total`, `page`, `limit`,
`total_pages`, `tipos_disponibles`, y `estadisticas_semaforo`,
`total_expedientes`, `expedientes_con_alertas` del alcance completo (sin filtros).

#### `GET /infraction/expedientes/alertas/{expediente_id}` (lectura)

```json
{"ok": true, "radicado": "2026ER00045", "alertas": {"respuesta_plazo": {}}, "total_alertas": 1,
 "estadisticas_semaforo": {"verde": 0, "amarillo": 1, "rojo": 0, "vencido": 0}}
```

**Correo semanal**: todos los lunes a las 8:00 (America/Bogota) se envía a
cada usuario con `infraccion_gestionar` el resumen de alertas de sus
expedientes (vía app-users). No es un endpoint.

### A.10 Descarga del expediente completo

#### `GET /infraction/expedientes/descargar/{expediente_id}` (lectura)

Devuelve **un solo PDF** (`application/pdf`,
`attachment; filename="infraccion_{radicado}_completo.pdf"`) armado por
app-docs, en este orden:

1. Radicado inicial.
2. Respuesta: documento del radicado; si hay medida preventiva, su acto y las
   citaciones/notificaciones de cada involucrado.
3. Informe técnico de visita (aceptado).
4. Concepto: solicitud de información, acto (+ citaciones/notificaciones +
   comunicación) y oficio remite.
5. Informe técnico de seguimiento.
6. Cierre: acto + citaciones/notificaciones.

Sin documentos → `404`. Error de app-docs → `500`.

### A.11 Auditoría — `GET /infraction/expedientes/auditoria/registros` (`auditoria_infracciones`)

| Param | Tipo | Filtro |
|---|---|---|
| `usuario_id` | int | |
| `nombre_usuario` | str | contiene (filtra en memoria) |
| `cedula` | str | contiene (filtra en memoria) |
| `expediente_radicado` | str | igual |
| `tipo_operacion` | `INSERT` \| `UPDATE` \| `DELETE` | prefijo de `tipo_evento` |
| `tabla_afectada` | str | contiene en `tipo_evento` |
| `id_registro` | int | `expediente_id` (no numérico → `400`) |
| `fecha_inicio`, `fecha_fin` | `YYYY-MM-DD` | inclusive (formato inválido → `400`) |
| `limit` | 1–1000 (default 100) | |
| `offset` | ≥ 0 (default 0) | |

Orden: más recientes primero.

```json
{
  "ok": true,
  "data": [{
    "id": 501, "usuario_id": 7, "usuario_nombre": "Laura Díaz",
    "usuario_documento": "1012345678", "usuario_correo": "laura@x.co",
    "tabla_afectada": "Expediente", "tipo_operacion": "UPDATE",
    "tipo_evento": "UPDATE_EXPEDIENTE_BASICO", "resultado": "OK",
    "descripcion": "Actualización completa de expediente ...",
    "expediente_radicado": "2026ER00045", "id_registro": 12,
    "fecha": "2026-02-12T10:00:00-05:00",
    "datos_anteriores": {}, "datos_nuevos": {}
  }],
  "pagination": {"total": 1, "limit": 100, "offset": 0, "has_more": false},
  "msg": "Se encontraron 1 registros"
}
```

`datos_*` con `abogado_responsable_id` / `encargado_id` se enriquecen con
`*_nombre` y `*_documento`. Los eventos sin prefijo de operación se mapean en
`routes/file_audit._TIPO_EVENTO_MAP_INF`. Por ejemplo,
`EDITAR_MATRIZ_RECURSOS` → `UPDATE` / "Matriz de recursos afectados", con
`datos_anteriores` / `datos_nuevos` = `{informe_id, matriz}`.

---

## B — Etapas — `/infraction/etapas`

Orden del proceso y condición para crear cada etapa:

| # | Etapa | Se puede crear cuando |
|---|---|---|
| 1 | Respuesta | Siempre |
| 2 | Informe técnico **VISITA** | Existe respuesta y, si requiere medida preventiva: la medida tiene acto y el acto tiene comunicación con documento |
| 3 | Acoger concepto | Informe de VISITA aceptado |
| 4 | Informe técnico **SEGUIMIENTO** | Concepto `AUTO_REQUERIMIENTO` con término calculado y vencido (`infraccion_super_gestion` no espera el término). Con `OFICIO` o `RESOLUCION_ARCHIVO` no aplica |
| 5 | Cierre | Concepto `AUTO_REQUERIMIENTO` + SEGUIMIENTO aceptado; o `RESOLUCION_ARCHIVO`; o `OFICIO` con oficio remite y su documento |

**Patrón de los GET de etapa**: lectura del expediente. Si la etapa no existe
responden `404` con el cuerpo:

```json
{"ok": false, "detail": "Etapa concepto no encontrada", "creable": true, "creable_msg": null}
```

`creable` dice si el botón de crear debe habilitarse y `creable_msg` el
motivo cuando no. Las escrituras exigen ser el encargado (`403` si no).

### B.1 Respuesta (etapa 1)

| Método | Ruta | Body / notas |
|---|---|---|
| GET | `/etapas/respuesta/{expediente_id}` | `404` sin `creable` si no existe |
| POST | `/etapas/respuesta/{expediente_id}` | `RespuestaBody`. Ya existe o radicado repetido → `409`. `201` |
| PUT | `/etapas/respuesta/{etapa_id}` | `RespuestaBody`. Ojo: id de la **etapa** |

`RespuestaBody`: `{radicado: str, fecha_radicado: date, documento_radicado_id: int, requiere_medida_preventiva: bool}`.
`radicado` es único entre respuestas.

```json
{
  "ok": true,
  "respuesta_data": {
    "id": 3, "expediente_id": 12, "radicado": "2026ER00100", "fecha_radicado": "2026-02-15",
    "documento_radicado_id": 120, "requiere_medida_preventiva": true, "fecha_creacion": "2026-02-15"
  },
  "medida_preventiva": {"ok": true, "medida": {"...": "ver B.2"}},
  "message": "Etapa respuesta creada correctamente"
}
```

- Si `requiere_medida_preventiva` y no hay medida, se crea una vacía.
- Si se desmarca, la medida se conserva en BD pero se responde
  `{"ok": false, "message": "No se requiere medida preventiva"}`.

### B.2 Medida preventiva (dentro de Respuesta)

| Método | Ruta | Notas |
|---|---|---|
| POST | `/etapas/medidas/{etapa_respuesta_id}` | Solo si la respuesta la requiere (`400`); ya existe → `409`. `201` |
| PUT | `/etapas/medidas/{medida_id}` | |

Body `MedidaBody`: `{tipo_medida_id: int, cantidad: str, especie: str, estado_medida: bool | null}`.

Respuesta (también en `medida_preventiva` de B.1):

```json
{
  "ok": true,
  "medida": {
    "id": 5, "etapa_respuesta_id": 3, "acto_administrativo_id": 40,
    "informacion": {
      "tipo_medida_id": 1, "cantidad": "2 m3", "especie": "Roble", "estado_medida": true,
      "tipo_medidas": [{"id": 1, "nombre": "DECOMISO"}]
    },
    "acto_admin": {"...": "ver C.1 — ActoFrontend"}
  }
}
```

El acto de la medida se crea con `POST /actos/administrativos` enviando
`medida_preventiva_id` (C.1).

### B.3 Informe técnico (etapas 2 y 4)

`tipo_informe` = `VISITA` | `SEGUIMIENTO`.

#### `GET /etapas/informe-tecnico/{expediente_id}/{tipo_informe}` (lectura)

```json
{
  "ok": true,
  "data": {
    "id": 8, "expediente_id": 12, "tipo_informe": "VISITA", "modo": "FLUJO",
    "profesional_asignado_id": 15, "profesional_nombre": "Carlos Ruiz",
    "revisor_asignado_id": 16, "revisor_nombre": "Marta Gil",
    "fecha_programacion_visita": "2026-03-01", "fecha_recibido_informe": null,
    "fecha_aceptacion_informe": null, "documento_informe_id": null,
    "fecha_creacion": "2026-02-20T08:00:00-05:00", "aceptado": false,
    "tiene_matriz": false, "recursos_afectados": null,
    "proceso_id": 30, "estado_proceso": {"codigo": "en_revision", "etiqueta": "En revisión", "tono": "info"},
    "proceso_activo": true, "numero_devoluciones": 0, "version_actual": 1, "requiere_mi_accion": false
  },
  "message": "Informe técnico obtenido correctamente"
}
```

- `modo`: `FLUJO` (asignación + revisión, sección D) o `MANUAL` (cargue directo).
- `recursos_afectados`: solo en VISITA aceptada con matriz diligenciada (D.5).
- Campos `proceso_*` / `requiere_mi_accion`: resumen del proceso de revisión
  vigente (todo `null`/`0`/`false` si no hay).

#### `POST /etapas/informe-tecnico/{expediente_id}/crear/{tipo_informe}` (encargado)

Crea el informe vacío (sin validar `creable`: el front solo muestra el botón
cuando el GET lo permite). Respuesta `200` con `data` del informe. Después,
el líder lo asigna (D.2) o el super gestor lo carga a mano (D.3).

### B.4 Acoger concepto (etapa 3)

`tipo_acogida_concepto` = `AUTO_REQUERIMIENTO` | `OFICIO` | `RESOLUCION_ARCHIVO`.

| Método | Ruta | Body / notas |
|---|---|---|
| GET | `/etapas/concepto/{expediente_id}` | |
| POST | `/etapas/concepto/{expediente_id}` | `{tipo_acogida_concepto}`. Sin VISITA aceptada → `400`; ya existe → `409`. `201` |
| PUT | `/etapas/concepto/{etapa_concepto_id}` | `{tipo_acogida_concepto, dias_termino?}` |

```json
{
  "ok": true,
  "data": {
    "id": 6, "expediente_id": 12, "tipo_acogida_concepto": "AUTO_REQUERIMIENTO",
    "dias_termino": 30, "fecha_termino_calculada": "2026-04-20",
    "acto_administrativo_id": 41, "fecha_creacion": "2026-03-05T10:00:00-05:00",
    "acto_admin": {"...": "ActoFrontend"},
    "oficio_remite": null,
    "solicitud_informacion": {"id": 2, "radicado": "2026EE0123", "fecha_radicado": "2026-03-06", "archivo_solicitud_id": 140,
                              "radicado_respuesta": "2026ER0456", "fecha_radicado_respuesta": "2026-03-20",
                              "archivo_respuesta_id": 151}
  }
}
```

PUT:

- `dias_termino` ∈ {10, 15, 30, 60, 120} y solo con `AUTO_REQUERIMIENTO`
  (si no → `400`). `fecha_termino_calculada` = hoy + `dias_termino` días hábiles.
- **Cambiar el tipo borra** el acto (con notificaciones y comunicación), el
  oficio remite y la etapa de **Cierre**; reinicia el término. La solicitud de
  información se conserva. Respuesta con `cierre_eliminado: true` y mensaje
  que lo indica.

El acto del concepto se crea con `POST /actos/administrativos` +
`etapa_concepto_id` (C.1).

#### Oficio remite (solo concepto `OFICIO`)

| Método | Ruta | Notas |
|---|---|---|
| POST | `/etapas/oficio-remite/{etapa_concepto_id}` | Concepto no es `OFICIO` → `400`; ya existe → `409`. `201` |
| PUT | `/etapas/oficio-remite/{oficio_id}` | |

Body: `{radicado, fecha_radicado, fecha_remitido, archivo_remite_id}`.

#### Solicitud de información (cualquier tipo de concepto)

| Método | Ruta | Notas |
|---|---|---|
| POST | `/etapas/solicitud-informacion/{etapa_concepto_id}` | Ya existe → `409`. `201` |
| PUT | `/etapas/solicitud-informacion/{solicitud_id}` | Agrega, reemplaza o quita la respuesta |
| DELETE | `/etapas/solicitud-informacion/{solicitud_id}` | Resta el uso de los archivos (solicitud y respuesta) |

Body: `{radicado, fecha_radicado, archivo_solicitud_id, radicado_respuesta?,
fecha_radicado_respuesta?, archivo_respuesta_id?}`. Las respuestas `201` /
`200` devuelven en `data` la solicitud completa (mismos campos que en el GET).

**Respuesta del usuario** (opcional): `radicado_respuesta` (formato
`AAAAER####` o `AAAAER#####`, p. ej. `2024ER0001`; se guarda en mayúsculas),
`fecha_radicado_respuesta` (no futura) y `archivo_respuesta_id` (PDF ya subido
a app-docs). Si llega uno de los tres, son obligatorios los tres (`400`);
vacíos o `null` los tres = sin respuesta. En el PUT, enviarlos vacíos quita la
respuesta y resta el uso de su archivo; cambiar el archivo resta el viejo y
suma el nuevo. El PDF de la respuesta entra en la descarga del expediente y se
resta en la cascada que borra la etapa de concepto.

Validaciones de oficio y solicitud: `radicado` con formato
`AAAAEE####` o `AAAAEE#####` (p. ej. `2024EE0001`); fechas `YYYY-MM-DD` no
futuras (si no → `400`).

### B.5 Cierre (etapa 5)

| Método | Ruta | Notas |
|---|---|---|
| GET | `/etapas/cierre/{expediente_id}` | |
| POST | `/etapas/cierre/{expediente_id}` | Sin body. Condición no cumplida → `400` con el motivo; ya existe → `409`. `201` |

```json
{"ok": true, "data": {"id": 4, "expediente_id": 12, "acto_administrativo_id": null,
 "fecha_creacion": "2026-05-01T09:00:00-05:00", "acto_admin": null}}
```

El acto de cierre se crea con `POST /actos/administrativos` + `etapa_cierre_id` (C.1).

### B.6 Migración a sancionatorio

#### `GET /etapas/migracion/medida/{radicado}`

La consume app-sancionatoria al crear su medida preventiva. Permiso:
`sancionatorio_gestionar` o `infraccion_consultar` (cualquier radicado);
`infraccion_gestionar` solo los suyos. Sin permiso → `403`.

```json
{
  "ok": true,
  "medida": {"tipo_medida_id": 1, "cantidad": "2 m3", "especie": "Roble", "estado_medida": true},
  "informe_tecnico_documento_id": 130,
  "acto": {
    "tipo_acto": "RES", "numerado": 15, "fecha_numerado": "2026-02-20",
    "documento_acto_administrativo_id": 125,
    "comunicacion": {"numerado": 16, "fecha_numerado": "2026-02-21", "fecha_envio": "2026-02-22", "documento_comunicacion_id": 126}
  }
}
```

Si falta algo responde **`200`** con `{"ok": false, "detail": "..."}`
(expediente inexistente, sin medida preventiva, medida no registrada).
`acto` y `comunicacion` solo vienen si tienen documento.

---

## C — Actos administrativos — `/infraction/actos`

Un acto pertenece a **una** de: medida preventiva, concepto o cierre. El acto
**nace del proceso de revisión** (C.4): el encargado del expediente lo proyecta,
el líder de proyecto lo aprueba para firma y la versión final firmada crea el
acto. `POST /actos/administrativos` queda como **cargue directo de super
gestión**. Las notificaciones y comunicaciones (C.2, C.3) siguen exigiendo ser
el encargado. Todas las escrituras usan **`multipart/form-data`** (Form), no
JSON — salvo los DELETE de notificación y comunicación, que reciben
`{"expediente_id": N}` en el **body JSON**.

Validaciones comunes:

- `numerado`: entero de máximo 4 dígitos (`400`).
- Si el año de `fecha_numerado` es > 2012, el par (`numerado`, `fecha_numerado`)
  es único dentro de su tipo (actos, notificaciones) → `400` si ya está en uso.
- `expediente_id` debe coincidir con el expediente del acto/etapa → `400`.

**ActoFrontend** (como lo devuelven las etapas en `acto_admin`):

```json
{
  "id": 41, "tipo_acto": "AUTO", "numerado": "15", "fecha_numerado": "2026-03-10",
  "documento_acto_administrativo_id": 150, "fecha_creacion": "2026-03-10T11:00:00-05:00",
  "etapa_id": 0, "nivel_auxiliar": null,
  "notificacion": {"id": 0, "fecha_creacion": "", "involucrados": [{
    "id": 9, "involucrado_id": 20, "numerado": "16", "fecha_numerado": "2026-03-11",
    "fecha_envio_citacion": "2026-03-12", "fecha_constancia_citacion": "2026-03-15",
    "notificacion_exitosa": true, "documento_citacion_id": 151, "documento_notificacion_id": 152,
    "tipo_notificacion_id": 1, "fecha_notificacion": null, "fecha_creacion": "..."
  }]},
  "comunicacion": {"id": 3, "numerado": "17", "fecha_numerado": "2026-03-12",
                   "fecha_envio": "2026-03-13", "fecha_creacion": "...", "documento_comunicacion_id": 153}
}
```

`notificacion` es `null` si no hay notificaciones; `comunicacion`, `null` si
no hay. `etapa_id`/`nivel_auxiliar` son fijos (compatibilidad con el
componente compartido con sancionatorio).

### C.1 Acto administrativo

#### `POST /actos/administrativos` (`infraccion_super_gestion`: cargue directo)

Crea el acto **sin revisión**. Sin super gestión → `403` (el encargado usa
C.4). Si la etapa tiene un proceso de revisión vigente, se cierra
(`finalizado` si no había terminado) y queda en el histórico (`activo = false`).

| Campo (Form) | Tipo | |
|---|---|---|
| `expediente_id` | int | obligatorio |
| `medida_preventiva_id` | int | uno de estos tres |
| `etapa_concepto_id` | int | |
| `etapa_cierre_id` | int | |
| `etapa_id` | int | alias de `etapa_concepto_id` (legado) |
| `tipo_acto` | `AUTO` \| `RES` | |
| `numerado` | int | |
| `fecha_numerado` | `YYYY-MM-DD` | |
| `documento_acto_administrativo_id` | int | |

Enviar concepto y cierre a la vez, o ninguno (sin medida) → `422`. La etapa ya
tiene acto → `400`. Respuesta `201`:

```json
{"ok": true, "data": {"id": 41, "numerado": 15, "fecha_numerado": "2026-03-10",
 "documento_acto_id": 150, "tipo_acto": "AUTO", "fecha_creacion": "..."}}
```

#### `PUT /actos/administrativos/{acto_id}` (encargado o super gestión)

Form: `tipo_acto`, `numerado`, `fecha_numerado`, `expediente_id?`,
`documento_acto_administrativo_id?`. El encargado corrige tipo, numerado y
fecha; cambiar el documento (PDF) es **solo de super gestión** (`403` para el
encargado; si cambia se mueve el uso del archivo). Misma respuesta que el POST (`200`).

#### `DELETE /actos/administrativos/{acto_id}` (`infraccion_super_gestion`)

Borra el acto y sus notificaciones (resta usos de acto, citaciones y
notificaciones) y lo desliga de su etapa. El proceso de revisión del acto
queda en el histórico (`activo = false`) y el encargado puede proyectar uno
nuevo. Sin super gestión → `403`. Respuesta `{"ok": true, "data": {tipo_acto, numerado, fecha_numerado, etapa_tipo}}`.

### C.2 Notificación (una por involucrado y acto)

#### `POST /actos/notificaciones`

| Campo (Form) | Tipo | |
|---|---|---|
| `expediente_id`, `acto_admin_id`, `involucrado_id` | int | |
| `numerado` | int | |
| `fecha_numerado`, `fecha_envio_citacion` | `YYYY-MM-DD` | |
| `fecha_constancia_citacion` | `YYYY-MM-DD` | opcional |
| `documento_citacion_id` | int | |
| `notificacion_exitosa` | bool (default `false`) | |
| `tipo_notificacion_id` | int | obligatorio si exitosa |
| `documento_notificacion_id` | int | obligatorio si exitosa; se ignora si no |

Ya existe para ese involucrado en ese acto → `400`. Respuesta `201` con
`data` = la notificación (`id`, `acto_administrativo_id`, `involucrado_id`,
fechas, documentos, `notificacion_exitosa`, `tipo_notificacion_id`,
`fecha_creacion`).

#### `PUT /actos/notificaciones/{notificacion_id}`

Mismos campos salvo `acto_admin_id` e `involucrado_id`. Si se desmarca
`notificacion_exitosa` se quita `documento_notificacion_id` (y su uso).

#### `DELETE /actos/notificaciones/{notificacion_id}`

Body JSON `{"expediente_id": 12}` (sin él → `422`). Resta usos de citación y
notificación. Respuesta `{"ok": true, "data": {...datos borrados}}`.

### C.3 Comunicación (una por acto)

| Método | Ruta | Campos |
|---|---|---|
| POST | `/actos/comunicaciones` | Form: `expediente_id`, `acto_admin_id`, `numerado`, `fecha_numerado`, `fecha_envio`, `documento_comunicacion_id`. Ya existe → `409`. `201` |
| PUT | `/actos/comunicaciones/{comunicacion_id}` | Form: los mismos sin `acto_admin_id` |
| DELETE | `/actos/comunicaciones/{comunicacion_id}` | Body JSON `{"expediente_id": N}` |

Respuesta: `{"ok": true, "data": {id, acto_administrativo_id, numerado, fecha_numerado, fecha_envio, documento_comunicacion_id}}`.

### C.4 Proceso de revisión del acto — `/infraction/revision-actos`

Aplica a los tres actos (medida preventiva, acoger concepto, cierre). Reglas
(`services/revision_actos.py`):

- **Sube versiones** solo el **encargado actual** del expediente
  (`expediente.abogado_responsable_id`), comprobado en cada acción: si se
  reasigna el expediente, el nuevo encargado continúa el proceso y el anterior
  ya no puede subir (`403`).
- **Revisa** cualquier usuario con `infraccion_lider_proyecto` (por permiso,
  sin asignación; puede ser el mismo encargado). Acciones: `aprobado_firma` o
  `devuelto` (comentario obligatorio, adjunto opcional `.pdf/.doc/.docx` con
  las observaciones). No hay aprobación directa (`aprobado` → `400`).
- Tras una devolución, la corrección debe ser un archivo que **no esté ya** en
  el proceso (`409`) y **vuelve a revisión**: nunca se aprueba sola. **Sin
  tope** de devoluciones (`max_devoluciones` = 9999 en el detalle).
- Aprobado para firma, el encargado carga la **versión final** (PDF firmado +
  tipo, numerado y fecha): se auto-aprueba y se crea el acto en la etapa, en
  una sola transacción (audita `CREAR_ACTO_ADMIN`).

| Código | Etiqueta | Siguiente paso |
|---|---|---|
| `pendiente_carga` | Pendiente de carga | El encargado sube la primera versión (`POST .../versiones`) |
| `en_revision` | En revisión | El líder de proyecto aprueba para firma o devuelve |
| `rechazado` | Devuelto | El encargado sube la corrección (`POST .../versiones`) |
| `aprobado_firma` | Aprobado para firma | El encargado carga la versión final (`POST .../version-final`) |
| `aprobado` | Aprobado (final) | Acto creado |
| `finalizado` | Finalizado (final) | Super gestión cargó el acto directo (C.1) |

Quién ve un proceso: el encargado actual, quien lo proyectó, quien lo revisó y
cualquiera con `infraccion_lider_proyecto`, `infraccion_consultar` o
`infraccion_super_gestion`. Sin acceso, inexistente o proceso de informe → `403`.

`ProcesoActoDetalle` = `ProcesoDetalle` del paquete compartido (como en D.4) +
`etapa_tipo`, `etapa_ref_id`, `tipo_documento`, `expediente_id`,
`expediente_radicado`, `activo`, `encargado_id`, `encargado_nombre`, `acto_id`
y `puede_cargar_version_final` (soy el encargado y está aprobado para firma).
`revisores` lista a los líderes de proyecto actuales.

Cadena de revisión (mismo formato que recurso): `paso_actual` (1),
`total_pasos` (1) y `pasos`, con un único paso:

```json
"pasos": [{"numero": 1, "estado": "actual",
           "permisos": [{"permiso": "infraccion_lider_proyecto", "etiqueta": "Líder de proyecto",
                         "revisado": false, "revisor_id": null, "revisor_nombre": null,
                         "accion": null, "fecha_revision": null}]}]
```

`estado` del paso: `completado` cuando está aprobado para firma (o ya
aprobado); si no, `actual`. Una devolución lo deja otra vez `actual`. En
`revisado`/`revisor_*` aparece el líder que lo aprobó para firma en el ciclo
vigente.

#### `GET /revision-actos/etapa/{etapa_tipo}/{etapa_ref_id}`

`etapa_tipo`: `medida_preventiva` | `etapa_concepto` | `etapa_cierre` (otro →
`400`); etapa inexistente → `404`. Lo ve el encargado o quien tenga
`infraccion_lider_proyecto`, `infraccion_consultar` o super gestión (`403`).

```json
{"ok": true, "etapa_tipo": "etapa_cierre", "etapa_ref_id": 5, "expediente_id": 12,
 "acto_id": null, "encargado_id": 7, "encargado_nombre": "Ana Pérez",
 "es_encargado": true, "puede_proyectar": false,
 "puede_cargue_directo": false, "proceso": {"...": "ProcesoActoDetalle | null"}}
```

`puede_proyectar`: soy el encargado, la etapa no tiene acto y no hay proceso
en curso. `puede_cargue_directo`: super gestión y la etapa sin acto.
`encargado_id` / `encargado_nombre`: abogado responsable actual del expediente
(`null` si no tiene); la etapa lo muestra aunque aún no haya proceso.

#### `GET /revision-actos/{proceso_id}` → `ProcesoActoDetalle`

#### `POST /revision-actos/iniciar` (encargado)

Form: `etapa_tipo`, `etapa_ref_id`. Abre el proceso del acto en
`pendiente_carga` (versión 0), como los procesos de recurso: la primera
versión se sube después desde el modal del proceso con
`POST /{proceso_id}/versiones`. Es lo que usa el botón "Subir versión" de la
etapa. **Idempotente**: si ya hay un proceso en curso lo devuelve (`200`); si
lo crea, `201` (un proceso anterior ya terminado pasa al histórico). No es el
encargado → `403`; la etapa ya tiene acto → `409`; etapa inexistente → `404`.
Respuesta: `{"ok": true, "proceso_id", "creado", "estado"}`. No avisa a nadie
(el aviso a los líderes sale al subir la v1).

#### `POST /revision-actos/proyectar` (encargado)

Atajo de `iniciar` + primera versión en una sola llamada.

Form: `etapa_tipo`, `etapa_ref_id`, `archivo` (`.pdf/.doc/.docx`),
`comentario?`. Crea el proceso con la v1 en `en_revision` y avisa a los líderes
de proyecto. No es el encargado → `403`; la etapa ya tiene acto o hay proceso
en curso → `409`; formato no permitido → `400`. Un proceso anterior ya
terminado (p. ej. super gestión eliminó el acto) pasa al histórico. Respuesta
`201`: `{"ok": true, "proceso_id", "estado", "message"}`.

#### `POST /revision-actos/{proceso_id}/revisiones` (líder de proyecto)

Form: `accion` (`aprobado_firma` | `devuelto`), `comentario`, `adjunto?`.
Proceso no vigente → `409`. Respuesta como D.4 (`estado`, `numero_devoluciones`).

#### `POST /revision-actos/{proceso_id}/versiones` (encargado actual)

Form: `archivo`, `comentario?`. Primera versión (`pendiente_carga`, tras
`iniciar`) o corrección (`rechazado`) (`400` en otro estado;
`409` en `aprobado_firma`, que va por `version-final`; `409` si el archivo ya
está en el proceso). Queda `en_revision` y avisa a los líderes.

#### `POST /revision-actos/{proceso_id}/version-final` (encargado actual)

Form: `archivo` (PDF), `tipo_acto` (`AUTO` | `RES`), `numerado` (1–4 dígitos),
`fecha_numerado` (`YYYY-MM-DD`), `comentario?`. Todo se valida **antes** de
subir el archivo: no es PDF / datos inválidos / numerado ya usado → `400`; no
está en `aprobado_firma` o la etapa ya tiene acto → `409`. El archivo cuenta un
uso por la versión y otro por el acto.

```json
{"ok": true, "proceso_id": 31, "version": 3, "version_id": 77,
 "estado": {"codigo": "aprobado", "etiqueta": "Aprobado", "tono": "success"},
 "acto": {"id": 41, "tipo_acto": "AUTO", "numerado": 15, "fecha_numerado": "2026-11-10", "documento_acto_id": 150},
 "message": "Versión firmada cargada: acto administrativo creado"}
```

#### Descargas

`GET /revision-actos/{proceso_id}/versiones/{version_id}/descarga` y
`GET /revision-actos/{proceso_id}/revisiones/{revision_id}/adjunto`, mismo
acceso que el detalle y mismas respuestas que en D.4.

#### Notificaciones in-app

Después del commit, `tipo = "acto_infraccion"`, `id_vinculada` = id del proceso:

| Evento | Destinatario |
|---|---|
| Proyectado / nueva versión | Líderes de proyecto (menos quien sube) |
| Devuelto | Encargado actual (indica si hay documento de observaciones) |
| Aprobado para firma | Encargado actual |
| Versión final (acto creado) | Líderes de proyecto |
| Reasignación del expediente con acto en curso | Nuevo encargado (A.6) |

Borrar la etapa (cambio de modo del informe o de tipo de concepto) borra
también los procesos de su acto y resta los usos de sus archivos.

### C.5 Mis actuaciones — `GET /infraction/mis-actuaciones`

Pantalla "Mis actuaciones" (antes Mis informes). Requiere
`infraccion_tecnico`, `infraccion_lider_tecnico`, `infraccion_lider_proyecto`
o `infraccion_gestionar` (si no → `403`). Una sola lista sin paginar (el
filtro es en cliente): primero lo que requiere mi acción, luego lo más reciente.

- **Informes** (técnico / líder técnico): los de `GET /informes/mios` (D.1);
  el ítem va completo en `informe`.
- **Actos**: rol `encargado` en los procesos de expedientes que tengo a cargo
  hoy o que proyecté (histórico); rol `revisor` (líder de proyecto) en los que
  revisé o están vigentes en revisión. Requieren mi acción: como encargado
  actual, `rechazado` o `aprobado_firma`; como líder, `en_revision`.

```json
{"ok": true, "data": {
  "actuaciones": [{
    "clave": "acto-31", "categoria": "acto", "tipo_documento": "ACTO_CIERRE",
    "tipo_etiqueta": "Acto de cierre", "expediente_id": 12, "expediente_radicado": "2026ER00045",
    "roles": [{"codigo": "encargado", "etiqueta": "Encargado"}],
    "proceso_id": 31, "estado_proceso": {"codigo": "rechazado", "etiqueta": "Devuelto", "tono": "warning"},
    "proceso_activo": true, "numero_devoluciones": 1, "version_actual": 1,
    "requiere_mi_accion": true, "accion_pendiente": "Subir la versión corregida",
    "fecha_actualizacion": "2026-11-19T10:00:00-05:00",
    "informe": null,
    "acto": {"etapa_tipo": "etapa_cierre", "etapa_ref_id": 5, "vigente": true, "acto_id": null, "soy_encargado_actual": true}
  }],
  "conteos": {"total": 1, "requieren_accion": 1},
  "filtros": {"tipos_documento": [{"codigo": "...", "etiqueta": "..."}],
              "estados": [{"codigo": "...", "etiqueta": "...", "tono": "..."}],
              "roles": [{"codigo": "acto:encargado", "etiqueta": "Encargado"}]}
}}
```

En los informes, `roles` usa `encargado` = técnico y `revisor` = líder técnico
(etiquetas "Técnico" / "Líder técnico") y `clave` = `informe-{id}`.

---

## D — Informes técnicos

Un informe técnico (VISITA o SEGUIMIENTO) se crea vacío desde la etapa (B.3) y
se completa por uno de dos **modos**:

- **FLUJO** (por defecto): el líder (`infraccion_asignar_informes`) asigna un
  técnico (`profesional_*`) y un líder técnico (`revisor_*`) → se crea un
  **proceso de revisión** → el técnico sube versiones y el líder técnico
  aprueba **para firma** o devuelve (no hay aprobación directa). Con el informe
  aprobado para firma, el técnico carga la **versión final** firmada (PDF) y,
  en VISITA, la **matriz de recursos afectados** (obligatoria): el informe
  queda **aceptado** (`fecha_aceptacion_informe`) con ese PDF.
- **MANUAL**: `infraccion_super_gestion` carga directamente el PDF, las
  fechas y, en VISITA, la matriz (expedientes históricos), sin revisión.

En campos y rutas se conservan los nombres `profesional` / `revisor`
(= técnico / líder técnico).

### D.1 Listados

#### `GET /infraction/informes` (`infraccion_asignar_informes`)

Solo informes en modo `FLUJO`. Query params: `fecha_desde`, `fecha_hasta`
(ISO, sobre la creación), `aceptado` (bool), `profesional_id`,
`expediente_radicado` (contiene), `tipo_informe`, `page` (≥ 1),
`limit` (1–100, default 20). Orden: más recientes primero.

```json
{
  "ok": true,
  "data": [{
    "id": 8, "expediente_id": 12, "expediente_radicado": "2026ER00045",
    "profesional_asignado_id": 15, "profesional_nombre": "Carlos Ruiz",
    "revisor_asignado_id": 16, "revisor_nombre": "Marta Gil",
    "modo": "FLUJO", "tipo_informe": "VISITA",
    "fecha_programacion_visita": "2026-03-01", "fecha_recibido_informe": null,
    "fecha_aceptacion_informe": null, "documento_informe_id": null,
    "fecha_creacion": "...", "aceptado": false,
    "proceso_id": 30, "estado_proceso": {"codigo": "pendiente_carga", "etiqueta": "Pendiente de carga", "tono": "neutral"},
    "proceso_activo": true, "numero_devoluciones": 0, "version_actual": 0, "requiere_mi_accion": false
  }],
  "total": 1, "page": 1, "limit": 20, "total_pages": 1,
  "profesionales_disponibles": [{"id": 15, "nombre": "Carlos Ruiz"}],
  "revisores_disponibles": [{"id": 16, "nombre": "Marta Gil"}]
}
```

#### `GET /infraction/informes/mios` (`infraccion_tecnico` o `infraccion_lider_tecnico`)

Informes donde el usuario es técnico (con `infraccion_tecnico`) y/o líder
técnico (con `infraccion_lider_tecnico`). Sin paginación. La pantalla Mis
actuaciones ya no lo llama: usa `GET /mis-actuaciones` (C.5), que incluye
estas mismas filas en `informe` (más `fecha_actualizacion`). Cada ítem: `id`,
`expediente_id`, `expediente_radicado`, `tipo_informe`, `modo`,
`soy_profesional`, `soy_revisor`, fechas, `documento_informe_id`, `aceptado`,
`puede_editar_matriz` (VISITA aceptada, soy el técnico y el expediente aún no
tiene Acoger concepto; reemplaza a `puede_diligenciar_matriz`), `tiene_matriz`
y el resumen del proceso.

`requiere_mi_accion` es `true` cuando: soy el profesional y el proceso está en
`pendiente_carga`, `rechazado` o `aprobado_firma`; o soy el revisor y está en
`en_revision`.

#### `GET /infraction/informes/disponibles` (`infraccion_super_gestion`)

`{"ok": true, "profesionales_disponibles": [{id, nombre}], "revisores_disponibles": [{id, nombre}]}`
para el selector opcional del cargue manual.

### D.2 Asignación (`infraccion_asignar_informes`)

Body: `{profesional_id: int, revisor_id: int, fecha_programacion_visita?: "YYYY-MM-DD"}`.

Validaciones (`400`): el informe está en `MANUAL`; ya fue aceptado;
profesional = revisor; el profesional no tiene `infraccion_tecnico`;
el revisor no tiene `infraccion_lider_tecnico`. Informe inexistente → `404`.

| Método | Ruta | Comportamiento |
|---|---|---|
| POST | `/informes/{informe_id}/asignar` | Crea el proceso (`pendiente_carga`). Si ya hay uno vigente sin terminar → `409` (usar PUT). Si el vigente quedó `finalizado`, se archiva y se crea uno nuevo |
| PUT | `/informes/{informe_id}/asignar` | Reasigna: finaliza el vigente y crea uno nuevo en la misma transacción. Avisa al profesional anterior |

Respuesta: `{"ok": true, "informe_id": 8, "proceso_id": 30, "message": "..."}`.
Se notifica in-app al profesional y al revisor (`tipo = "informe_tecnico"`,
`id_vinculada` = id del informe).

### D.3 Modo y cargue manual (`infraccion_super_gestion`)

#### `GET /informes/{informe_id}/cambiar-modo/impacto`

Vista previa de lo que borraría cambiar de modo (para el diálogo de
confirmación). Además del propio informe, se borran las etapas
**posteriores**: desde VISITA → concepto, seguimiento y cierre; desde
SEGUIMIENTO → cierre.

```json
{"ok": true, "informe_id": 8, "etapas": [
  {"codigo": "concepto", "etiqueta": "Acoger concepto", "detalle": "1 acto administrativo, 2 notificaciones",
   "conteos": {"actos": 1, "notificaciones": 2}}
]}
```

#### `PUT /informes/{informe_id}/cambiar-modo`

Body `{"modo": "FLUJO" | "MANUAL"}` (otro → `400`). Mismo modo → `200` sin
cambios. Si no:

- Pasando a `MANUAL` se cierra el proceso de revisión vigente.
- Se limpian archivo, fechas, profesional, revisor y la matriz de recursos.
- Se borran en cascada las etapas posteriores (sin excepción por actos
  notificados).

Todo en una transacción; si app-docs no acepta la resta de usos → `502` y no
se borra nada.

```json
{"ok": true, "informe_id": 8, "modo": "MANUAL",
 "message": "Modo actualizado. También se eliminaron: Acoger concepto",
 "etapas_eliminadas": [{"codigo": "concepto", "...": "..."}]}
```

#### `POST /informes/{informe_id}/cargue-manual`

Solo si el informe está en `MANUAL` (si no → `400`).

| Campo | Tipo | Regla |
|---|---|---|
| `file_id` | int | PDF ya subido a app-docs |
| `fecha_recibido` | `YYYY-MM-DD` | |
| `fecha_aceptacion` | `YYYY-MM-DD` | ≥ `fecha_recibido` |
| `fecha_programacion_visita` | `YYYY-MM-DD` | opcional |
| `profesional_id` | int | opcional; con `infraccion_tecnico` |
| `revisor_id` | int | opcional; con `infraccion_lider_tecnico`; distinto del profesional |
| `recursos_afectados` | `FilaRecurso[]` | **obligatoria en VISITA** (matriz completa, reglas en D.5); se ignora en SEGUIMIENTO |

La matriz se valida antes de tocar archivos: si falta, está incompleta o es
inválida → `400` y no se guarda nada. Se puede reenviar para editar (si el
`file_id` no cambia no se tocan usos; la matriz se vuelve a enviar completa).
Respuesta `{"ok": true, "informe_id": 8, "message": "Informe técnico cargado y aceptado correctamente"}`.

### D.4 Proceso de revisión — `/infraction/revision-informes`

Estados del proceso (`estado.codigo`):

| Código | Etiqueta | Siguiente paso |
|---|---|---|
| `pendiente_carga` | Pendiente de carga | El técnico sube la v1 |
| `en_revision` | En revisión | El líder técnico aprueba para firma o devuelve |
| `rechazado` | Devuelto | El técnico sube una corrección |
| `aprobado_firma` | Aprobado para firma | El técnico carga la versión final (`POST .../version-final`: PDF firmado + matriz en VISITA) → se auto-aprueba |
| `aprobado` | Aprobado (final) | Informe aceptado (solo se llega por la versión final) |
| `finalizado` | Finalizado (final) | Se alcanzó el máximo de devoluciones (3) o se reasignó / cambió de modo; el líder debe reasignar |

Quién ve un proceso: el profesional, el asignador, sus revisores y cualquiera
con `infraccion_asignar_informes`. Sin acceso o inexistente → `403`.

#### `GET /revision-informes/por-informe/{informe_id}`

Proceso **vigente** del informe → `ProcesoInformeDetalle`. Sin proceso
vigente → `404 {"ok": false, "detail": "El informe no tiene un proceso de revisión vigente"}`
(o `403` si el usuario no es profesional, revisor ni asignador).

#### `GET /revision-informes/{proceso_id}`

`ProcesoInformeDetalle` de cualquier proceso (también los inactivos).

```json
{
  "id": 30, "nombre": "Informe VISITA - Expediente 2026ER00045", "descripcion": "...",
  "estado": {"codigo": "en_revision", "etiqueta": "En revisión", "tono": "info"},
  "version_actual": 1, "numero_devoluciones": 0, "max_devoluciones": 3,
  "creador_id": 15, "fecha_creacion": "...", "fecha_ultima_actualizacion": "...",
  "revisores": [{"revisor_id": 16, "nombre": "Marta Gil", "fecha_asignacion": "...", "notificado": true}],
  "versiones": [{"version_id": 50, "numero_version": 1, "usuario_subida_id": 15, "comentario": "",
                 "fecha_subida": "...", "archivo": {"file_id": 160, "url": "...", "nombre": "informe.docx", "size": 20480}}],
  "revisiones": [],
  "auditoria": [{"auditoria_id": 1, "usuario_id": 7, "accion": "crear", "accion_etiqueta": "Proceso creado",
                 "tono": "info", "descripcion": "...", "datos_adicionales": null, "fecha_accion": "..."}],
  "acciones_disponibles": [{"codigo": "aprobado_firma", "etiqueta": "Aprobar para firma", "tono": "success",
                            "requiere_comentario": false, "adjunto": {"permitido": false, "extensiones": []},
                            "bloqueada": null, "icono": "firmar"}],
  "subida_version": null,
  "informe_id": 8, "expediente_id": 12, "expediente_radicado": "2026ER00045",
  "tipo_informe": "VISITA", "modo": "FLUJO", "activo": true,
  "profesional_nombre": "Carlos Ruiz", "asignador_id": 7
}
```

- `versiones` y `revisiones`: más recientes primero; `auditoria`: cronológica.
- `acciones_disponibles` (para el usuario actual) y `subida_version`
  (`null` si no puede subir; si no, `{permitida, extensiones, motivo}`) son la
  **fuente de verdad** de los botones: el front no los deduce del estado.
- `subida_version` del técnico: en `en_revision` → `permitida: false` con el
  motivo "El informe está en revisión; podrás subir una nueva versión si te lo
  devuelven"; en `aprobado_firma` → `permitida: false`, `extensiones: [".pdf"]`
  y el motivo "Aprobado para firma: carga la versión firmada (PDF) con «Cargar
  versión final»". En ese estado el front muestra el formulario de versión
  final cuando `subida_version != null`.

#### `POST /revision-informes/{proceso_id}/versiones` (técnico asignado)

`multipart/form-data`: `archivo` (obligatorio), `comentario?`.

- Permitido en `pendiente_carga` y `rechazado`. En `aprobado_firma` → `409`
  (la firmada va por `version-final`); en otro estado → `400`. Si no es el
  técnico asignado → `403`.
- Extensiones: `.pdf`, `.doc`, `.docx`.
- El archivo se sube a app-docs (antivirus incluido). Vacío → `400`;
  > 50 MB → `413`; rechazado por app-docs → `400`; app-docs caído → `502`.

```json
{"ok": true, "proceso_id": 30, "informe_id": 8, "version": 2, "version_id": 51,
 "estado": {"codigo": "en_revision", "etiqueta": "En revisión", "tono": "info"},
 "message": "Versión subida exitosamente"}
```

#### `POST /revision-informes/{proceso_id}/version-final` (técnico asignado)

Con el proceso en `aprobado_firma`, carga la versión firmada y acepta el
informe en una sola transacción. Equivale a la "versión final" del concepto
en app-recurso. `multipart/form-data`:

| Campo | Regla |
|---|---|
| `archivo` | obligatorio; **PDF** (si no → `400`) |
| `recursos_afectados` | JSON (string) con la matriz `FilaRecurso[]`; **obligatoria en VISITA** (reglas en D.5); se ignora en SEGUIMIENTO |
| `comentario` | opcional |

Orden de validación: técnico asignado (`403`) → proceso activo en
`aprobado_firma` (`409`) → matriz (`400`: falta, JSON mal formado, incompleta
o inválida) → PDF (`400`). Después: subida a app-docs → versión `n+1` →
auto-aprobación (`aprobado`) → informe aceptado → matriz guardada. Si algo
falla antes de subir, no se sube nada.

```json
{"ok": true, "proceso_id": 30, "informe_id": 8, "version": 2, "version_id": 52,
 "estado": {"codigo": "aprobado", "etiqueta": "Aprobado", "tono": "success"},
 "informe_aceptado": true, "tiene_matriz": true,
 "message": "Versión firmada cargada: informe aceptado"}
```

#### `POST /revision-informes/{proceso_id}/revisiones` (líder técnico asignado)

`multipart/form-data`: `accion`, `comentario?`, `adjunto?`.

| `accion` | Efecto |
|---|---|
| `aprobado_firma` | → `aprobado_firma` (admite borrador Word). Luego el técnico carga la versión final |
| `devuelto` | → `rechazado`. `comentario` obligatorio; admite `adjunto` (`.pdf/.doc/.docx`). A la 3.ª devolución → `finalizado` |

`aprobado` ya **no** es una acción del líder técnico
(`400 "Acción de revisión inválida: aprobado"`). Una acción desconocida o un
adjunto en una acción que no lo admite → `400`.

```json
{"ok": true, "proceso_id": 30, "informe_id": 8,
 "estado": {"codigo": "aprobado_firma", "etiqueta": "Aprobado para firma", "tono": "success"},
 "numero_devoluciones": 0, "message": "..."}
```

Al aceptarse el informe (versión final) se fijan `fecha_aceptacion_informe`
(hoy), `fecha_recibido_informe` (fecha de subida de la versión) y
`documento_informe_id`, y se avisa al abogado responsable del expediente.

Datos existentes: los procesos que ya estaban en `en_revision` siguen igual y
se cierran por `aprobado_firma` + versión final. Los informes aceptados antes
sin matriz quedan así y se completan con la edición (D.5).

#### Descargas (mismo acceso que el detalle)

| Ruta | Descarga |
|---|---|
| `GET /revision-informes/{proceso_id}/versiones/{version_id}/descarga` | Archivo de una versión |
| `GET /revision-informes/{proceso_id}/revisiones/{revision_id}/adjunto` | Adjunto de una devolución |

Respuesta en streaming con `Content-Disposition: attachment`. No existe → `404`;
app-docs caído → `502`.

#### Notificaciones in-app

Se envían después del commit (si fallan no deshacen la operación), con
`tipo = "informe_tecnico"` e `id_vinculada` = id del informe:

| Evento | Destinatario |
|---|---|
| Asignación / reasignación | Técnico y líder técnico (y el técnico anterior al reasignar) |
| Nueva versión | Líderes técnicos |
| Devuelto | Técnico (`n/3`, indica si hay adjunto) |
| Aprobado para firma | Técnico |
| Versión final (informe aceptado) | Líderes técnicos y el abogado responsable |
| Finalizado por devoluciones | Técnico, asignador y líderes técnicos ("reasignar") |

### D.5 Matriz de recursos afectados (solo VISITA)

Una fila por recurso: `AIRE`, `SUELO`, `AGUA`, `PAISAJE`, `FLORA`, `FAUNA`,
`RUIDO`, `SOCIAL`, `OTRO`. Se diligencia **al aceptar** el informe
(`version-final` en FLUJO, `cargue-manual` en MANUAL) y ahí es obligatoria.
Validación común (`services/matriz_recursos.py`), siempre sobre la matriz
**completa**:

- `FilaRecurso = {recurso, magnitud?, reversibilidad?, no_existe = false}`.
- `magnitud` ∈ `LEVE`, `MODERADO`, `GRAVE`; `reversibilidad` ∈ `REVERSIBLE`,
  `IRREVERSIBLE`.
- Cada fila marca `no_existe` o trae magnitud **y** reversibilidad.
- Una fila por recurso. Recurso inválido o repetido → `400`. Si faltan
  recursos → `400 "Falta diligenciar en la matriz: ..."`. Si está vacía →
  `400 "La matriz de recursos afectados es obligatoria en los informes de VISITA"`.

#### `GET /infraction/informes/{informe_id}/recursos`

Acceso: profesional o revisor del informe, `infraccion_asignar_informes` o el
abogado responsable del expediente (si no → `403`).

```json
{"ok": true, "data": [{"recurso": "AIRE", "magnitud": "LEVE", "reversibilidad": "REVERSIBLE", "no_existe": false}]}
```

#### `PUT /infraction/informes/{informe_id}/recursos` (editar matriz)

Edita **solo la matriz** de un informe de VISITA ya aceptado. El informe
(PDF, fechas) no se edita aquí. Pueden editarla:

- el **técnico asignado**, mientras el expediente **no** tenga la etapa
  Acoger concepto. Después → `400 "El expediente ya tiene la etapa Acoger
  concepto: la matriz ya no se puede editar"`;
- `infraccion_super_gestion`, si el informe es `MANUAL` (sin ese límite).

Cualquier otro usuario → `403`.

Body `{"filas": [FilaRecurso, ...]}` con la matriz completa (reglas arriba).
Hace upsert por recurso y deja auditoría `EDITAR_MATRIZ_RECURSOS`
(antes/después). Respuesta `{"ok": true, "message": "Matriz de recursos afectados guardada correctamente"}`.

Errores: `400` (no es VISITA, no está aceptado, ya existe Acoger concepto o la
matriz es inválida), `403`, `404`.

---

## E — Integraciones (no HTTP para el front)

| Servicio | Para qué |
|---|---|
| app-users | `verify_permission`, usuarios por permiso, nombres/documentos, notificaciones in-app (`exp_infraccion`, `informe_tecnico`, `acto_infraccion`) y correo semanal de alertas |
| app-docs | Datos de archivos, `increment/decrement` de usos, subida/descarga de versiones de informes y actos y PDF unificado del expediente |
| app-involved | Datos de las personas (`bulk`); si falla, los listados se muestran sin ellas |
| app-sancionatoria | Consume `GET /etapas/migracion/medida/{radicado}` (B.6) |

Las llamadas salientes usan `x-service-token` firmado como
`infraction-service`. app-infraction no expone endpoints service-to-service
(`EXPECTED_CALLERS` vacío).
