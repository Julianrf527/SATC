# API de app-recurso (Concesiones de Aguas)

El front llama todo con el prefijo del gateway **`/recurso`** (p. ej.
`GET /recurso/mis-documentos`). Autenticación: cookie de sesión → el gateway
inyecta `x-gateway-token`, `X-Gateway-User-Id`, `X-Gateway-Role-Id`.
Errores: `{"detail": "mensaje"}` con el código HTTP indicado.

## A — Base y expediente

Reglas comunes de la sección A:

- Respuestas exitosas: `{"ok": true, "data": ...}` (algunas con `message`).
- Permisos: **lectura** = `recurso_consultar` o `recurso_gestionar` o
  `recurso_super_gestion`; **gestión** = `recurso_gestionar` o
  `recurso_super_gestion` (V1). Sin permiso → `403`. Sin headers del gateway → `403`.
- Bloqueo optimista: todo registro editable trae `version`. Al editar/borrar
  el front envía la `version` que leyó; si otra persona lo cambió antes →
  `409 {"detail": "Fue modificado por otra persona, recarga"}`. Tras un 409
  hay que recargar el registro (`GET /recurso/expedientes/{id}`).
- Archivos: el front sube el PDF a app-docs (`/documents/files/...`, igual que
  infraction) y envía aquí solo el `file_id`. El backend registra el uso.
- `acciones_disponibles`: listas de códigos que el front usa para mostrar
  botones; el front no recalcula reglas.
- Formato de fechas: `YYYY-MM-DD` (fechas) e ISO 8601 (timestamps).

### A.1 Catálogos — `/recurso/catalogos` (lectura)

| Método | Ruta | Respuesta `data` |
|---|---|---|
| GET | `/recurso/catalogos` | `{municipios, tipos_fuente, fuentes, usos, tipos_notificacion}` (todos juntos, para el formulario) |
| GET | `/recurso/catalogos/municipios` | `[{id, nombre, veredas: [{id, nombre}]}]` (ordenados por nombre) |
| GET | `/recurso/catalogos/tipos-fuente` | `[{id, nombre}]` (SUPERFICIAL, LÓTICO, LÉNTICO, SUBTERRÁNEO) |
| GET | `/recurso/catalogos/fuentes` | `[{id, nombre}]` (NACIMIENTO, QUEBRADA, RÍO, …) |
| GET | `/recurso/catalogos/usos` | `["DOMESTICO", "PECUARIO", "ABREVADERO", "AGRICOLA", "RIEGO", "INDUSTRIAL", "ACUICULTURA", "SILVICULTURA", "RECREATIVO", "INSTITUCIONAL", "OTRO"]` |
| GET | `/recurso/catalogos/tipos-notificacion` | `[{id, nombre}]` (AVISO, ELECTRÓNICA, PERSONAL) |

Ejemplo `GET /recurso/catalogos/municipios`:

```json
{"ok": true, "data": [{"id": 1, "nombre": "Almeida", "veredas": [{"id": 1, "nombre": "Belen"}]}]}
```

Errores: `403`.

### A.2 Expedientes — consulta (lectura)

#### `GET /recurso/expedientes`

Listado paginado (pestañas Gestionar y Consulta). Query params (todos opcionales):

| Param | Tipo | Filtro |
|---|---|---|
| `page` | int ≥ 1 (default 1) | |
| `limit` | int 1–200 (default 10) | |
| `radicado` | str | contiene, sin distinguir mayúsculas |
| `expediente` | str | contiene (p. ej. `CA 001`) |
| `numero_vital` | str | contiene |
| `municipio_id` | int | municipio de la vereda |
| `vereda_id` | int | |
| `involucrado_id` | int | id de app-involved (solicitante o tercero). Para buscar por nombre/documento: buscar primero la persona en app-involved (`/involveds/...`) y pasar su id |

Orden: más recientes primero (`fecha_creacion` desc).

```json
{
  "ok": true,
  "data": [{
    "id": 7, "version": 1,
    "radicado": "2026ER00012", "fecha_radicado": "2026-03-10",
    "expediente": "CA 001-26", "numero_vital": "VITAL-123",
    "nombre_predio": "La Esperanza", "nombre_fuente": "Juancho Castro",
    "fecha_creacion": "2026-03-10T09:12:00-05:00",
    "vereda": {"id": 1, "nombre": "Belen"},
    "municipio": {"id": 1, "nombre": "Almeida"},
    "tipo_fuente": {"id": 1, "nombre": "SUPERFICIAL"},
    "involucrados": [{"involucrado_id": 3, "tipo_vinculo": "SOLICITANTE", "nombre": "Ana Pérez",
                      "tipo_documento": "CC", "numero_documento": 1020304050}]
  }],
  "page": 1, "limit": 10, "totalCount": 1
}
```

Errores: `403`, `422` (params inválidos).

#### `GET /recurso/expedientes/{id}`

Información base completa + etapas.

```json
{
  "ok": true,
  "data": {
    "id": 7, "version": 3,
    "radicado": "2026ER00012", "fecha_radicado": "2026-03-10",
    "expediente": "CA 001-26", "numero_vital": "VITAL-123",
    "nombre_predio": "La Esperanza", "matricula_inmobiliaria": "078-12345",
    "codigo_catastral": "15001000100020003",
    "radicado_oficio_entrada": "2026ER90012", "fecha_oficio_entrada": "2026-03-01",
    "doc_comprobante_pago_id": 101,
    "comprobante_pago": {"file_id": 101, "nombre": "Comprobante de pago"},
    "vereda": {"id": 1, "nombre": "Belen"},
    "municipio": {"id": 1, "nombre": "Almeida"},
    "tipo_fuente": {"id": 1, "nombre": "SUPERFICIAL"},
    "nombre_fuente": "Juancho Castro",
    "fuentes": [{"id": 2, "nombre": "QUEBRADA"}],
    "usos": ["DOMESTICO", "RIEGO"],
    "fecha_creacion": "2026-03-10T09:12:00-05:00",
    "involucrados": [{
      "id": 15, "expediente_id": 7, "involucrado_id": 20,
      "tipo_vinculo": "SOLICITANTE",
      "representante_id": 21, "acto_admin_id": null,
      "fecha_vinculacion": "2026-03-10T09:20:00-05:00",
      "version": 1,
      "involucrado": {"id": 20, "tipo_documento": "NIT", "numero_documento": 900123456,
                      "digito_verificacion": "3", "nombre": "Acueducto Veredal",
                      "celular": null, "correo": null, "direccion": null},
      "representante": {"id": 21, "tipo_documento": "CC", "nombre": "Pedro Gómez", "...": "..."},
      "requiere_representante": true,
      "acciones_disponibles": ["editar_representante", "desvincular"]
    }],
    "acciones_disponibles": ["editar_informacion_base", "vincular_solicitante", "descargar_expediente"],
    "etapas": {}
  }
}
```

- `involucrados[].involucrado` / `representante`: datos de app-involved. Si
  app-involved no responde llegan como `{"id": N}` (la pantalla debe
  renderizar igual).
- `requiere_representante`: `true` si la persona es NIT (V14).
- `involucrados[].acciones_disponibles`: solo en vínculos `SOLICITANTE` y si
  el usuario puede gestionar; los terceros intervinientes se gestionan en la
  sección C.
- `acciones_disponibles` del expediente: `editar_informacion_base`,
  `vincular_solicitante` (gestión), `descargar_expediente` (siempre).
- `etapas`: árbol de etapas; su forma la define la **sección C**.

Errores: `403`, `404`.

### A.3 Expedientes — crear y editar (gestión)

Body común (`ExpedienteDatos`, todos obligatorios; los textos se recortan y no
pueden quedar vacíos):

| Campo | Tipo | Regla |
|---|---|---|
| `radicado` | str ≤ 15 | único |
| `fecha_radicado` | date | |
| `expediente` | str ≤ 9 | único, p. ej. `"CA 001-26"` |
| `numero_vital` | str ≤ 20 | |
| `nombre_predio` | str ≤ 50 | |
| `matricula_inmobiliaria` | str ≤ 20 | |
| `codigo_catastral` | str ≤ 30 | |
| `radicado_oficio_entrada` | str ≤ 20 | radicado de la solicitud |
| `fecha_oficio_entrada` | date | |
| `doc_comprobante_pago_id` | int | `file_id` de app-docs; debe ser **PDF** |
| `vereda_id` | int | catálogo |
| `tipo_fuente_id` | int | catálogo |
| `nombre_fuente` | str ≤ 50 | nombre propio, texto libre |
| `fuente_ids` | int[] (≥ 1) | catálogo `fuentes`; repetidos se ignoran |
| `usos` | str[] (≥ 1) | valores de `usos`; repetidos se ignoran |

#### `POST /recurso/expedientes`

Crea el expediente (nace con el comprobante de pago). Respuesta `201`:

```json
{"ok": true, "message": "Expediente creado", "data": {"id": 7, "expediente": "CA 001-26", "version": 1}}
```

Errores:
- `400`: vereda / tipo de fuente / fuentes inexistentes; comprobante no
  encontrado en app-docs o no es PDF.
- `403`: sin permiso de gestión.
- `409`: `"Ya existe un expediente con el radicado X"` /
  `"Ya existe un expediente con el número de expediente X"` (también si dos
  personas lo crean a la vez).
- `422`: campo faltante, vacío, demasiado largo o uso inválido.
- `502`: app-docs no registró el uso del comprobante (no se crea nada).

#### `PUT /recurso/expedientes/{id}`

Edita la información base completa, incluidas fuentes y usos (se reemplazan
por las listas enviadas), bajo el mismo `version`. Body: `ExpedienteDatos` +
`"version": int`. Si cambia `doc_comprobante_pago_id` se valida el nuevo PDF
y se ajusta el contador de usos (+1 nuevo, −1 anterior).

```json
{"ok": true, "message": "Expediente actualizado", "data": {"id": 7, "version": 4}}
```

Errores: `400` (catálogos / comprobante), `403`, `404`, `409` (versión vieja,
radicado o número de expediente de otro expediente), `422`, `502`.

### A.4 Solicitantes — `/recurso/involucrados` (plan §3, V14)

Las personas se buscan/crean en app-involved (`/involveds/...`, igual que en
infraction) y aquí se vincula su `id`.

#### `GET /recurso/involucrados/expediente/{expediente_id}` (lectura)

Query opcional `tipo_vinculo=SOLICITANTE|TERCERO_INTERVINIENTE`. `data`: lista
de vínculos con la misma forma que `involucrados` en `GET /expedientes/{id}`.
Errores: `403`, `404`.

#### `POST /recurso/involucrados/vinculos` (gestión)

```json
{"expediente_id": 7, "involucrado_id": 20, "representante_id": 21}
```

`representante_id` es opcional salvo que la persona sea **NIT** (V14).
`recurso_super_gestion` puede omitirlo. Respuesta `201`: `{"ok": true,
"message": "Solicitante vinculado", "data": <vínculo>}`.

Errores:
- `400`: persona NIT sin `representante_id`.
- `403`; `404`: expediente, persona o representante inexistentes.
- `409`: la persona ya está vinculada a este expediente (como solicitante o tercero).
- `502`: app-involved no responde (no se puede validar).

#### `PATCH /recurso/involucrados/vinculos/{vinculo_id}/representante` (gestión)

```json
{"representante_id": 22, "version": 1}
```

`representante_id: null` quita el representante (no permitido si es NIT).
Respuesta: `{"ok": true, "data": {"id": 15, "representante_id": 22, "version": 2}}`.
Errores: `400` (NIT sin representante; vínculo de tercero interviniente),
`403`, `404`, `409` (versión vieja), `502`.

#### `DELETE /recurso/involucrados/vinculos/{vinculo_id}?version=N` (gestión)

Desvincula un solicitante. Respuesta: `{"ok": true, "message": "Solicitante
desvinculado", "data": {"id": 15}}`.

Errores: `400` (vínculo de tercero interviniente), `403`, `404`, `409`
(versión vieja; o la persona ya tiene notificaciones registradas en el
expediente o un acto que la reconoce — `TODO(negocio)`: confirmar qué hacer en
esos casos; hoy se bloquea y no se borra nada), `422` (falta `version`).

### A.5 Descarga del expediente completo (lectura)

#### `GET /recurso/expedientes/{id}/documentos`

Índice de los documentos que entran en la descarga, en el mismo orden:

```json
{"ok": true, "data": [
  {"file_id": 101, "descripcion": "Comprobante de pago"},
  {"file_id": 140, "descripcion": "Auto que admite No. 15"},
  {"file_id": 141, "descripcion": "Comunicación de Auto que admite"}
]}
```

#### `GET /recurso/expedientes/{id}/descargar`

PDF único (`application/pdf`, `Content-Disposition: attachment;
filename="concesion_CA_001-26_completo.pdf"`). Usar como descarga de blob
(como infraction). Orden: comprobante de pago → auto admite (acto,
comunicación, citaciones/notificaciones, oficio Alcaldía, fijación del aviso,
constancia de fijación, anexos) → actos que reconocen terceros → concepto
técnico + anexos → requerimiento (acto, respuesta, concepto adicional) →
decisión → recurso de reposición (escrito, acto) → memorias de cálculo
(planos, concepto, requerimiento, subsanación, acto) → recibo de obras
(informes, conceptos, requerimiento, acto). Solo documentos finales (no las
versiones en revisión). Un archivo repetido aparece una vez.

Errores: `403`, `404` (expediente inexistente o sin documentos), `502`
(app-docs no generó el PDF).

## B — Revisión de documentos, Mis informes y actos

Reglas comunes:

- `ProcesoDetalle.acciones_disponibles` y `subida_version` se calculan **por
  usuario** en el backend: el front no deduce botones del estado.
- Estados del proceso (`estado.codigo`): `pendiente_carga` (Pendiente de carga),
  `en_revision` (En revisión), `rechazado` (Devuelto), `aprobado_firma`
  (Aprobado para firma), `aprobado` (Aprobado), `finalizado` (Finalizado, solo
  por cierre forzado). Cada uno llega con `etiqueta` y `tono`
  (`info|success|warning|error|neutral`).
- Cadenas de revisión (`tipo_documento` → pasos; en cada paso revisan **todos**
  los permisos, en cualquier orden):

  | tipo_documento | etapa_tipo | Pasos |
  |---|---|---|
  | `AUTO_ADMITE`, `REQUERIMIENTO`, `APRUEBA_MEMORIAS` | acto_admite / requerimiento / memorias_calculo | líder jurídico → líder del proyecto |
  | `DECISION`, `RECURSO` | decision / recurso_reposicion | líder jurídico → líder del proyecto **y** asesora de subdirección |
  | `RECONOCE_TERCERO`, `APRUEBA_OBRAS` | expediente_involucrado / recibo_satisfaccion_obras | provisional: como AUTO_ADMITE (`TODO(negocio)`) |
  | `CONCEPTO_ETAPA2` | concepto_tecnico | líder técnico **y** SIG → líder del proyecto |
  | `CONCEPTO_ADICIONAL`, `CONCEPTO_MEMORIAS`, `CONCEPTO_SUBSANACION`, `CONCEPTO_OBRAS`, `CONCEPTO_OBRAS_SEGUNDO` | concepto_tecnico | líder técnico |

- Flujo: el proceso nace en `pendiente_carga` al asignarse el encargado (lo crea
  la etapa). El encargado sube versiones aquí; en `aprobado_firma` la versión
  firmada **no** se sube aquí sino con "Cargar versión final" de la etapa
  (sección C), que la deja `aprobado` y crea el acto.
- Quien devuelve cuenta como "ya revisó" en ese paso: al subir la corrección,
  si en el paso no queda nadie pendiente, el documento avanza solo (si era el
  último paso queda `aprobado_firma`). Sin tope de devoluciones (`TODO(negocio)`;
  `max_devoluciones` = 9999).

### B.1 Revisión — `/recurso/revision-documentos`

Equivalente a `/infraction/revision-informes`: el adapter de
`@features/proceso-revision` es el mismo que el de infraction cambiando las rutas.

| Método | Ruta | Permiso | Descripción |
|---|---|---|---|
| GET | `/revision-documentos/{proceso_id}` | ver (*) | Detalle `ProcesoDocumentoDetalle` |
| GET | `/revision-documentos/por-etapa/{etapa_tipo}/{etapa_ref_id}` | ver (*) | Detalle del proceso vigente de una fila de etapa |
| POST | `/revision-documentos/{proceso_id}/versiones` | encargado del documento | Subir versión (multipart) |
| POST | `/revision-documentos/{proceso_id}/revisiones` | permiso de revisor pendiente del paso actual | Aprobar / aprobar para firma / devolver (multipart) |
| GET | `/revision-documentos/{proceso_id}/historial` | ver (*) | `{ok, data: {versiones, revisiones}}` |
| GET | `/revision-documentos/{proceso_id}/auditoria` | ver (*) | `{ok, data: [auditoría]}` |
| GET | `/revision-documentos/{proceso_id}/versiones/{version_id}/descarga` | ver (*) | Archivo (stream) |
| GET | `/revision-documentos/{proceso_id}/revisiones/{revision_id}/adjunto` | ver (*) | Adjunto de una devolución (stream) |

(*) **ver** = encargado del documento, quien tenga algún permiso de revisor de
su cadena, o `recurso_consultar` / `recurso_gestionar` / `recurso_super_gestion`.
Si no puede ver (o el id no existe) → **403** "No tienes acceso a este documento".

#### Detalle — `ProcesoDocumentoDetalle`

Es `ProcesoDetalle` (tipos `frontend/src/features/proceso-revision/types.ts`)
más campos propios:

```json
{
  "id": 7, "nombre": "Decisión - Expediente CA 012-26", "descripcion": "Etapa 4 · Decisión. ...",
  "estado": {"codigo": "en_revision", "etiqueta": "En revisión", "tono": "info"},
  "version_actual": 2, "numero_devoluciones": 1, "max_devoluciones": 9999, "creador_id": 30,
  "fecha_creacion": "2026-10-09T10:00:00-05:00", "fecha_ultima_actualizacion": "...",
  "revisores": [{"revisor_id": 40, "nombre": "Ana", "fecha_asignacion": "...", "notificado": false}],
  "versiones": [{"version_id": 12, "numero_version": 2, "archivo": {"file_id": 345, "url": "/files/345", "nombre": "decision.docx", "size": 1234},
                 "usuario_subida_id": 30, "comentario": "", "fecha_subida": "..."}],
  "revisiones": [{"revision_id": 5, "revisor_id": 40, "revisor_nombre": "Ana", "accion": "devuelto",
                  "accion_etiqueta": "Devuelto", "tono": "warning", "comentarios": "Corregir",
                  "version_revisada": 1, "fecha_revision": "...", "adjunto": null,
                  "paso": 1, "permiso": "recurso_lider_juridico", "permiso_etiqueta": "Líder jurídico"}],
  "auditoria": [{"auditoria_id": 1, "usuario_id": 30, "accion": "crear", "accion_etiqueta": "Proceso creado",
                 "tono": "info", "descripcion": "...", "datos_adicionales": {}, "fecha_accion": "..."}],
  "acciones_disponibles": [
    {"codigo": "aprobado", "etiqueta": "Aprobar", "tono": "success", "requiere_comentario": false,
     "adjunto": {"permitido": false, "extensiones": []}, "bloqueada": null, "icono": "aprobar"},
    {"codigo": "devuelto", "etiqueta": "Devolver", "tono": "warning", "requiere_comentario": true,
     "adjunto": {"permitido": true, "extensiones": [".pdf", ".doc", ".docx"]}, "bloqueada": null, "icono": "devolver"}
  ],
  "subida_version": null,

  "expediente_id": 3, "expediente_radicado": "2026ER00012", "expediente_codigo": "CA 012-26",
  "tipo_documento": "DECISION", "tipo_documento_etiqueta": "Decisión",
  "etapa_tipo": "decision", "etapa_etiqueta": "Etapa 4 · Decisión", "etapa_ref_id": 9,
  "activo": true, "encargado_id": 30, "encargado_nombre": "Luis",
  "paso_actual": 2, "total_pasos": 2,
  "pasos": [
    {"numero": 1, "estado": "completado", "permisos": [
      {"permiso": "recurso_lider_juridico", "etiqueta": "Líder jurídico", "revisado": true,
       "revisor_id": 40, "revisor_nombre": "Ana", "accion": "devuelto", "fecha_revision": "..."}]},
    {"numero": 2, "estado": "actual", "permisos": [
      {"permiso": "recurso_lider_proyecto", "etiqueta": "Líder del proyecto", "revisado": false, ...},
      {"permiso": "recurso_asesora_subdireccion", "etiqueta": "Asesora de subdirección", "revisado": true, ...}]}
  ]
}
```

- `paso_actual` es 1-based. `pasos[].estado`: `completado | actual | pendiente`.
- `revisores`: quienes ya revisaron + los usuarios con los permisos pendientes del paso actual.
- `acciones_disponibles` (solo en `en_revision`):
  - le toca (tiene un permiso pendiente del paso): `["aprobado", "devuelto"]`, o
    `["aprobado_firma", "devuelto"]` si su aprobación completa el último paso.
  - tiene permiso de la cadena pero ya revisó en este paso, o su paso es
    posterior: las mismas dos con `bloqueada` = motivo ("Ya revisaste…",
    "Aún no es tu turno. Pendiente de: …").
  - en otro caso: `[]`.
- `subida_version` (solo para el encargado; `null` para los demás):
  `pendiente_carga`/`rechazado` → `{permitida: true, extensiones: [".pdf", ".doc", ".docx"]}`;
  `en_revision` / `aprobado_firma` / finales → `permitida: false` + `motivo`
  (en `aprobado_firma`: "carga la versión firmada (PDF) … con \"Cargar versión final\"").

`GET /por-etapa/...` sin proceso vigente: **404** `{"ok": false, "detail": "La etapa no tiene un proceso de revisión vigente"}` (403 si el usuario no tiene ningún permiso de lectura ni de revisor).

#### Subir versión — `POST /revision-documentos/{id}/versiones`

`multipart/form-data`: `archivo` (File, obligatorio), `comentario` (opcional).
El backend lo sube a app-docs (igual que infraction).

```json
{"ok": true, "proceso_id": 7, "version": 2, "version_id": 12,
 "estado": {"codigo": "en_revision", "etiqueta": "En revisión", "tono": "info"},
 "paso_actual": 1, "message": "Versión subida exitosamente"}
```

Errores: 403 no es el encargado; 409 estado no admite subida (en revisión,
`aprobado_firma` → usar "Cargar versión final", proceso no vigente); 400
formato (pdf/doc/docx), archivo vacío o rechazado por app-docs; 409 versión
duplicada (mismo archivo); 413 > 50 MB; 502 app-docs.

#### Revisar — `POST /revision-documentos/{id}/revisiones`

`multipart/form-data`: `accion` (`aprobado` | `aprobado_firma` | `devuelto`),
`comentario` (obligatorio al devolver), `adjunto` (File opcional, solo al
devolver: pdf/doc/docx). Se revisa con el primer permiso pendiente del paso
actual que tenga el usuario. `aprobado` enviado por el último pendiente del
último paso también deja `aprobado_firma`.

```json
{"ok": true, "proceso_id": 7, "accion": "aprobado", "permiso": "recurso_lider_juridico",
 "estado": {"codigo": "en_revision", "etiqueta": "En revisión", "tono": "info"},
 "paso_actual": 2, "avanzo_paso": true, "numero_devoluciones": 0,
 "message": "Aprobado por Líder jurídico: paso 1 completo, pasa al paso 2"}
```

Errores: **403** sin ningún permiso de revisor de la cadena; **409** ya revisó
en este paso / no es su paso / el documento ya no está en revisión / proceso no
vigente (dos revisores con el mismo permiso a la vez: uno 200 y el otro 409);
**400** acción inválida, comentario faltante, adjunto no permitido,
`aprobado_firma` fuera del último paso.

Notificaciones (app-users, `tipo="recurso_doc"`, `id_vinculada` = id del
proceso): a los usuarios con los permisos pendientes cuando el documento entra
a revisión o avanza de paso; al encargado cuando lo devuelven o queda aprobado
para firma.

### B.2 Mis informes — `GET /recurso/mis-documentos`

Cualquier usuario autenticado (ve solo lo suyo; sin nada a cargo → lista vacía).
Igual que "Mis Informes" de infraction: UNA lista con TODOS los documentos del
usuario, en cualquier estado y vigentes o no (`activo = false`: cerrados o
reemplazados, su histórico; vienen con `proceso_activo = false` y nunca
requieren acción).

- **Encargado**: procesos donde soy el `creador_id`. Requiere mi acción si el
  proceso está vigente y en `pendiente_carga` ("Proyectar y subir la primera
  versión"), `rechazado` ("Subir la versión corregida") o `aprobado_firma`
  ("Cargar la versión firmada desde la etapa").
- **Revisor**: procesos cuya cadena incluye algún permiso de revisor mío y en
  los que ya registré una revisión, o que están vigentes, `en_revision` y con el
  paso actual pidiendo un permiso mío aún sin revisar (esto último requiere mi
  acción: "Revisar el documento"). Un líder NO ve todo lo de su cadena.
- Encargado y revisor del mismo proceso → **una sola fila** con
  `roles = ["encargado", "revisor"]` (como infraction, que marca Profesional /
  Revisor en la misma fila); `rol` = rol principal (encargado primero). Con el
  filtro `rol`, `roles`, `requiere_mi_accion` y `accion_pendiente` se limitan a ese rol.

Query: `rol` = `encargado` | `revisor` (opcional); `solo_accion` (bool, default
`false`); `expediente` (radicado o código CA, parcial); `tipo_documento`;
`estado`; `page` (≥1, default 1) y `limit` (1–100, default 20), como el
listado de informes de infraction.

Orden: primero los que requieren mi acción; luego por `fecha_ultima_actualizacion` desc.
`conteos` es sobre todo el conjunto filtrado (antes de `solo_accion` y de
paginar); `total` / `total_pages` son de la lista paginada (después de `solo_accion`).

```json
{
  "ok": true,
  "data": {
    "documentos": [{
      "proceso_id": 7, "rol": "encargado", "roles": ["encargado"],
      "accion_pendiente": "Subir la versión corregida",
      "tipo_documento": "DECISION", "tipo_documento_etiqueta": "Decisión",
      "estado_proceso": {"codigo": "rechazado", "etiqueta": "Devuelto", "tono": "warning"},
      "proceso_activo": true, "paso_actual": 1, "total_pasos": 2, "permisos_pendientes": [],
      "numero_devoluciones": 1, "version_actual": 1, "encargado_id": 30,
      "soy_encargado": true, "puedo_revisar": false, "requiere_mi_accion": true,
      "expediente_id": 3, "expediente_radicado": "2026ER00012", "expediente_codigo": "CA 012-26",
      "etapa_tipo": "decision", "etapa_etiqueta": "Etapa 4 · Decisión", "etapa_ref_id": 9,
      "etapa_padre": "decision", "etapa_padre_etiqueta": "...", "sub_proceso": null,
      "nombre": "Decisión - Expediente CA 012-26",
      "fecha_creacion": "...", "fecha_ultima_actualizacion": "..."
    }],
    "conteos": {"total": 12, "requieren_accion": 3},
    "filtros": {"tipos_documento": [{"codigo": "AUTO_ADMITE", "etiqueta": "Auto que admite"}],
                "estados": [{"codigo": "pendiente_carga", "etiqueta": "Pendiente de carga", "tono": "neutral"}],
                "roles": [{"codigo": "encargado", "etiqueta": "Encargado"}, {"codigo": "revisor", "etiqueta": "Revisor"}]}
  },
  "total": 12, "page": 1, "limit": 20, "total_pages": 1
}
```

- `accion_pendiente` es `null` cuando no requiere mi acción.
- El botón de la fila abre el detalle con `proceso_id` (`/revision-documentos/{proceso_id}`).

### B.3 Actos, comunicación y notificación — `/recurso/actos`

Mismos campos y respuestas que infraction para usar `@features/acto-administrativo`
con este `ActoAdminEndpoints`:

```ts
{
  actoAdmin: {
    create: "/recurso/actos/administrativos",            // no existe: el acto lo crea la etapa (ver C)
    update: (id) => `/recurso/actos/administrativos/${id}`,
    delete: (id) => `/recurso/actos/administrativos/${id}`,
  },
  notificacion: { base: "/recurso/actos/notificaciones", delete: (id) => `/recurso/actos/notificaciones/${id}` },
  comunicacion: {
    create: "/recurso/actos/comunicaciones",
    update: (id) => `/recurso/actos/comunicaciones/${id}`,
    delete: (id) => `/recurso/actos/comunicaciones/${id}`,
  },
}
```

**Permiso de escritura**: `recurso_gestionar` (V1) **y** ser el encargado de la
etapa dueña del acto (`encargado_acto_id`; para el acto que reconoce al tercero,
el encargado de su proceso de revisión) — o `recurso_super_gestion`. Si no → 403
"Solo el encargado de la etapa (o super gestión) puede gestionar este acto".
Lectura: `recurso_consultar`/`recurso_gestionar`/super gestión.
`expediente_id` enviado distinto al del acto → 400 "El expediente no corresponde
al acto administrativo". Numerados: entero positivo de máx. 4 dígitos (el front
envía `"0012"`). Fechas `AAAA-MM-DD`.

| Método | Ruta | Permiso | Body |
|---|---|---|---|
| GET | `/actos/tipos-notificacion` | autenticado | — |
| GET | `/actos/administrativos/{acto_id}` | lectura | — |
| PUT | `/actos/administrativos/{acto_id}` | escritura | multipart: `expediente_id?`, `tipo_acto?` (se ignora), `numerado`, `fecha_numerado`, `documento_acto_administrativo_id?` |
| DELETE | `/actos/administrativos/{acto_id}?expediente_id=` | **solo super gestión** | — |
| POST | `/actos/comunicaciones` | escritura | multipart: `expediente_id`, `acto_admin_id`, `numerado`, `fecha_numerado`, `fecha_envio`, `documento_comunicacion_id` |
| PUT | `/actos/comunicaciones/{id}` | escritura | multipart: `expediente_id`, `numerado`, `fecha_numerado`, `fecha_envio`, `documento_comunicacion_id` |
| DELETE | `/actos/comunicaciones/{id}` | escritura | JSON `{"expediente_id": n}` |
| POST | `/actos/notificaciones` | escritura | multipart: ver abajo |
| PUT | `/actos/notificaciones/{id}` | escritura | multipart: ver abajo (+ `version` opcional) |
| DELETE | `/actos/notificaciones/{id}` | escritura | JSON `{"expediente_id": n}` |

`GET /actos/tipos-notificacion` → `{"ok": true, "data": [{"id": 1, "nombre": "PERSONAL"}, ...]}`.

`GET /actos/administrativos/{id}` →

```json
{"ok": true, "data": {
  "id": 4, "tipo_acto": "AUTO_ADMITE", "numerado": 12, "fecha_numerado": "2026-04-01",
  "documento_acto_administrativo_id": 345, "documento_acto_id": 345, "fecha_creacion": "...",
  "etapa_tipo": "acto_admite", "etapa_id": 2, "expediente_id": 3,
  "comunicacion": {"id": 1, "acto_administrativo_id": 4, "numerado": 3, "fecha_numerado": "2026-04-02",
                   "fecha_envio": "2026-04-03", "documento_comunicacion_id": 346,
                   "fecha_creacion": "2026-10-14T09:02:15-05:00"},
  "notificacion": {"id": 4, "fecha_creacion": "...", "involucrados": [ /* filas de notificación */ ]},
  "notificado": false,
  "involucrados_notificables": [{"involucrado_id": 501, "tipo_vinculo": "SOLICITANTE", "ya_notificado": false,
                                 "datos": {"id": 501, "nombre": "...", "tipo_documento": "CC", "...": "..."}}],
  "acciones_disponibles": ["editar_acto", "editar_comunicacion", "eliminar_comunicacion"]
}}
```

**Comunicar vs. notificar** (regla del área, 14/10/2026; una sola definición:
`ACTOS_SOLO_COMUNICACION` en `services/actos.py`, replicada en el front por
`seComunica` de `etapas/comun/actoFeature.ts`): **solo se comunican** —y nunca se
notifican— `AUTO_ADMITE` y `RECONOCE_TERCERO`; todos los demás actos **solo se
notifican** y no llevan comunicación. `POST /actos/notificaciones` sobre un acto que
solo se comunica → 400 "Este acto solo se comunica; no se notifica";
`POST /actos/comunicaciones` sobre un acto que solo se notifica → 400 "Este acto
solo se notifica; no se comunica".

`acciones_disponibles` posibles: `editar_acto`, `eliminar_acto` (solo super
gestión), `crear_comunicacion` (solo actos que se comunican) | `editar_comunicacion`
+ `eliminar_comunicacion` (si ya existe, aunque sea un dato heredado),
`crear_notificacion` (solo actos que se notifican y si queda algún
solicitante/tercero sin notificación), `editar_notificacion`, `eliminar_notificacion`.
`[]` si no es encargado ni super gestión. Si la etapa no tiene encargado
(cargue histórico, C.9) solo super gestión gestiona el acto.

`PUT /actos/administrativos/{id}` (corrección) → `{"ok": true, "data": <acto como arriba sin notificables/acciones>}`.
El `tipo_acto` lo fija la etapa (el formulario heredado manda AUTO/RES y se ignora).
Errores: 409 numerado + fecha ya usados por otro acto del mismo tipo; 403; 400.

`DELETE /actos/administrativos/{id}`: solo super gestión (403 al encargado:
"…para corregirlo usa editar"); desenlaza la etapa y borra comunicación y
notificaciones. `TODO(negocio)`: confirmar si el encargado puede eliminar.

**Comunicación** (una por acto, plan Etapa 1 paso 6) → `{"ok": true, "data": {id, acto_administrativo_id, numerado, fecha_numerado, fecha_envio, documento_comunicacion_id, fecha_creacion}}`
(201 al crear). 409 si el acto ya tiene comunicación. `fecha_creacion` = cuándo se
registró (columna nueva del 14/10/2026; `null` en comunicaciones anteriores).

**Notificación** (una fila por persona notificada). Campos multipart:
`expediente_id`, `acto_admin_id` (solo POST), `involucrado_id` (solo POST; id de
app-involved, debe estar vinculado al expediente como solicitante o tercero),
`numerado`, `fecha_numerado`, `fecha_envio_citacion`, `fecha_constancia_citacion`,
`documento_citacion_id` (**citación siempre obligatoria**), `notificacion_exitosa`
(`true|false`), `tipo_notificacion_id`, `fecha_notificacion`,
`documento_notificacion_id`, `version` (solo PUT, opcional).

Respuesta (forma `InvolucradoNotificacion` del front + `version`):

```json
{"ok": true, "data": {"id": 9, "acto_administrativo_id": 4, "acto_admin_id": 4, "involucrado_id": 501,
  "numerado": 45, "fecha_numerado": "2026-04-02", "fecha_envio_citacion": "2026-04-03",
  "fecha_constancia_citacion": "2026-04-04", "documento_citacion_id": 347,
  "notificacion_exitosa": true, "tipo_notificacion_id": 1, "documento_notificacion_id": 348,
  "fecha_notificacion": "2026-04-10", "fecha_creacion": "...", "version": 2}}
```

Errores: 400 involucrado no vinculado, fecha de constancia faltante, exitosa sin
tipo o sin documento de notificación, tipo inválido; 409 ya existe notificación
para esa persona en ese acto, numerado + fecha ya usados en otra notificación
(regla de infraction, desde 2013), `version` desactualizada. Si es exitosa y no
llega `fecha_notificacion`, se usa la fecha de hoy.

Los archivos (`documento_*_id`) los sube el front a app-docs antes (como
infraction); el backend lleva `numero_usos` (incrementa al asociar, decrementa al
reemplazar/borrar).

**Compensación del uso** (todas las escrituras, `services/usos_archivos.py`): el +1 se
hace antes del commit y el −1 de los reemplazados después. Cada +1 exitoso se anota en
la petición; si la operación termina en error (cualquier `4xx`/`5xx` por excepción o un
commit fallido) se resta exactamente lo sumado y no confirmado (best-effort, con log; la
respuesta conserva el error original). Un error posterior al commit no resta nada.

### B.4 API interna para C (no HTTP)

`services/revision_documentos.py` (ninguna función hace commit; errores
`ReviewError` con `status_code`/`detail`, traducir con `http_error(e)`):

| Función | Uso |
|---|---|
| `Avisos()` | Notificaciones best-effort tras el commit: `avisos.agregar(user_id, msg, proceso_id=)`, `agregar_permiso(permiso, msg, proceso_id=)`, `await avisos.enviar()` **después** de `commit` |
| `crear_proceso(db, *, expediente_id, tipo_documento, etapa_tipo, etapa_ref_id, encargado_id, usuario_id, avisos)` | Al asignarse el abogado / seleccionar el técnico. Deja `pendiente_carga` y avisa al encargado. 400 tipo inválido o de otra etapa; 409 `ProcesoYaExiste`. Carrera → `IntegrityError` del índice único parcial: envolver en `integridad_a_409` |
| `proceso_vigente(db, etapa_tipo, etapa_ref_id, para_actualizar=False)` | Proceso activo de la fila (o None). Bloquear antes el expediente |
| `procesos_vigentes(db, [(etapa_tipo, id), ...])` | Batch para el árbol de etapas → `{(etapa_tipo, id): proceso}` |
| `cargar_version_final(db, proceso, archivo: ArchivoRef, user_id, avisos, comentario=...)` | Dentro de la transacción de "Cargar versión final": exige `aprobado_firma`, PDF y que `user_id` sea el encargado; deja `aprobado` e incrementa el uso del archivo. 403/409/400/502 |
| `subir_a_docs(upload_file) -> ArchivoRef` / `archivo_ref_por_id(file_id, nombre=None)` | Construir el `ArchivoRef` desde un `UploadFile` o desde un `file_id` ya subido por el front |
| `resumen_proceso(db, proceso, user_id, permisos_usuario=None)` / `resumenes_procesos(db, procesos, user_id, permisos_usuario)` | Campos para el payload de cada etapa (misma forma que una fila de Mis informes sin datos de expediente; `RESUMEN_VACIO` si no hay proceso) |
| `permisos_de_usuario(user_id)` | Permisos de revisor del usuario (resolver una vez por petición y pasarlo a `resumenes_procesos`) |
| `cerrar_proceso_vigente(db, etapa_tipo, etapa_ref_id, *, usuario_id, descripcion)` | Finaliza y desactiva el proceso (super gestión carga directo, borrar etapa) |
| `CADENAS`, `cadena_de(tipo)`, `etiqueta_tipo_documento`, `etiqueta_etapa`, `etiqueta_permiso` | Catálogo de cadenas y etiquetas |

`services/actos.py`:

| Función | Uso |
|---|---|
| `crear_acto(db, *, tipo_acto, numerado, fecha_numerado, documento_id, user_id)` | Crea el acto (valida tipo, numerado 1..9999, fecha, documento; 409 numerado+fecha repetido del mismo tipo) e incrementa el uso del PDF. C enlaza `acto.id` en la etapa. `TODO(negocio)`: numeración por año |
| `etapa_de_acto(db, acto_id) -> EtapaActo \| None` | `etapa_tipo`, fila, `expediente_id`, `encargado_id` (busca en acto_admite, requerimiento, decision, recurso_reposicion, memorias_calculo, recibo_satisfaccion_obras, expediente_involucrado) |
| `involucrados_notificables(db, expediente_id)` | Solicitantes y terceros del expediente |
| `notificaciones_completas(db, acto_id)` → `{total, exitosas, notificado}` / `acto_notificado(db, acto_id)` | V13. `TODO(negocio)`: "notificado" = hay al menos una notificación y todas son exitosas |
| `serializar_acto(db, acto, etapa=None)` | Forma `ActoAdministrativo` del front (con comunicación y notificaciones) para el payload de la etapa |
| `acciones_acto(db, acto_id, usuario, etapa=None)` | Códigos de acciones del acto para el usuario |

## C — Etapas

Reglas comunes de la sección C:

- Respuestas de escritura: `{"ok": true, "message": "...", "data": {...}}` (normalmente
  `{id, version, proceso_id?, acto_id?}`). Tras cualquier escritura el front recarga
  el árbol con `GET /recurso/etapas/{expediente_id}` (o `GET /recurso/expedientes/{id}`).
- Permisos: escritura = `recurso_gestionar` o `recurso_super_gestion` (V1), salvo los
  endpoints del **técnico** (C.4), que exigen `recurso_tecnico` y NO `recurso_gestionar`
  (V3 manda sobre V1). Lectura = `recurso_consultar` / `recurso_gestionar` / super gestión.
- Errores: `400` regla de negocio §6 (el `detail` cita la regla, p. ej. "... (V7)") u
  orden del flujo, o archivo no PDF / no encontrado; `403` sin permiso o no es el
  encargado (V2) / técnico (V3); `404` etapa inexistente; `409` ya asignado
  (`"Ya fue asignado"`), ya existe, versión vieja (`"Fue modificado por otra persona,
  recarga"`), numerado+fecha repetido, o el documento aún no está aprobado para firma;
  `422` body inválido; `502` app-docs no registró el uso del archivo.
- Archivos: el front sube el PDF a app-docs y envía `file_id`. Todo documento de etapa
  debe ser **PDF** (entra a la descarga del expediente).
- Fechas `YYYY-MM-DD`. Numerado: entero 1..9999 (el front puede mandar `"0012"`).
- Super gestión omite en los endpoints normales las reglas §6 y del orden del flujo, y
  la V2 en las ediciones de datos; NO puede "cargar versión final" por otro (el motor de
  B exige que sea el encargado): para eso usa C.9.
- Concurrencia (§7): toda transición bloquea el expediente (`FOR UPDATE`); dos
  asignaciones / creaciones simultáneas → una `200` y otra `409`.

### C.1 Ciclo de un acto (patrón común)

1. **Asignarme** → crea la fila (o asigna atómicamente si ya existe sin encargado) y
   el proceso de revisión en `pendiente_carga` con el usuario como encargado.
2. Proyección y revisión con los endpoints de B (`/revision-documentos/*`), usando el
   `proceso.proceso_id` del nodo.
3. En `aprobado_firma` el encargado usa **version-final** con el PDF firmado y los
   datos escritos en él (`ActoFinal`):

```json
{"file_id": 345, "numerado": "0012", "fecha_numerado": "2026-04-01"}
```

   → el proceso queda `aprobado`, se crea el `acto_administrativo` con su `tipo_acto` y
   se enlaza en la etapa. Comunicación y notificaciones: `/actos/*` (B).

### C.2 Árbol de etapas — `GET /recurso/etapas/{expediente_id}` (lectura)

Misma información que `etapas` en `GET /recurso/expedientes/{id}`. `data`:

```json
{
  "etapa_actual": "decision",
  "etapa_actual_etiqueta": "Etapa 4 · Decisión",
  "orden": ["admite", "concepto", "requerimiento", "decision", "memorias", "obras"],
  "acciones_disponibles": ["vincular_tercero"],
  "admite": {
    "codigo": "admite", "etiqueta": "Etapa 1 · Auto que admite", "etapa_tipo": "acto_admite",
    "id": 3, "version": 4, "existe": true, "habilitada": true, "motivos_bloqueo": [],
    "encargado": {"id": 30, "nombre": "Luis"}, "tecnico": null,
    "datos": {"doc_oficio_alcaldia_id": 350, "doc_fijacion_aviso_id": 351,
              "doc_constancia_fijacion_aviso_id": 352},
    "proceso": {"proceso_id": 7, "tipo_documento": "AUTO_ADMITE",
                "estado_proceso": {"codigo": "aprobado", "etiqueta": "Aprobado", "tono": "success"},
                "paso_actual": 2, "total_pasos": 2, "permisos_pendientes": [], "...": "resumen de B"},
    "acto": {"id": 4, "tipo_acto": "AUTO_ADMITE", "numerado": 12, "fecha_numerado": "2026-04-01",
             "documento_acto_administrativo_id": 345, "comunicacion": null,
             "notificacion": {"id": 4, "involucrados": []}, "notificado": false,
             "acciones_disponibles": ["editar_acto", "crear_comunicacion"]},
    "anexos": [{"id": 1, "etapa_tipo": "acto_admite", "etapa_ref_id": 3, "nombre": "Acta",
                "documento_anexo_id": 360, "fecha_subida": "..."}],
    "acciones_disponibles": ["cargar_oficio_alcaldia", "cargar_fijacion_aviso",
                             "cargar_constancia_fijacion", "gestionar_anexos"]
  },
  "concepto": {"codigo": "concepto_etapa2", "tipo": "etapa2", "etapa_tipo": "concepto_tecnico",
               "tecnico": {"id": 32, "nombre": "Ana"},
               "datos": {"fecha_visita_tecnica": "2026-05-02", "fecha_aceptacion": "2026-05-20",
                         "caudal_fuente": 10.5, "caudal_disponible": 8.0, "caudal_otorgado": 1.2,
                         "num_usuarios": 3, "cumple": null, "doc_concepto_tecnico_id": 400},
               "campos": {"obligatorios": ["file_id", "fecha_aceptacion", "caudal_fuente", "caudal_disponible",
                                           "caudal_otorgado", "num_usuarios"],
                          "opcionales": [],
                          "campos": [{"campo": "fecha_aceptacion", "tipo": "fecha",
                                      "etiqueta": "Fecha del concepto (firma)", "obligatorio": true},
                                     {"campo": "caudal_fuente", "tipo": "decimal",
                                      "etiqueta": "Caudal fuente (L/s)", "obligatorio": true},
                                     {"...": "caudal_disponible, caudal_otorgado (decimal), num_usuarios (entero)"}]},
               "...": "resto de campos de nodo"},
  "requerimiento": {"codigo": "requerimiento", "ambito": "etapa3",
                    "datos": {"radicado_oficio_entrada": null, "fecha_oficio_entrada": null,
                              "doc_oficio_entrada_id": null},
                    "existe": false, "habilitada": true, "acciones_disponibles": ["asignarme"],
                    "concepto_adicional": {"codigo": "concepto_adicional", "tipo": "adicional", "...": "nodo"}},
  "decision": {"codigo": "decision",
               "datos": {"decision": "OTORGADA", "requiere_memorias": true, "fecha_ejecutoria": null},
               "recurso": {"codigo": "recurso", "etapa_tipo": "recurso_reposicion", "existe": false,
                           "habilitada": false,
                           "motivos_bloqueo": ["El recurso de reposición solo procede si la decisión está notificada (V13)"],
                           "datos": {"radicado": null, "fecha_radicado": null, "doc_recurso_id": null,
                                     "resultado": null}}},
  "memorias": {"codigo": "memorias", "etapa_tipo": "memorias_calculo",
               "datos": {"radicado": null, "fecha_radicado": null, "doc_planos_id": null},
               "acciones_disponibles": ["registrar_planos"],
               "concepto": {"tipo": "memorias", "...": "nodo concepto"},
               "requerimiento": {"ambito": "memorias", "...": "nodo acto"},
               "subsanacion": {"etapa_tipo": "subsanacion",
                               "datos": {"radicado": null, "fecha_radicado": null, "doc_planos_ajustados_id": null},
                               "concepto": {"tipo": "subsanacion", "...": "nodo concepto"}},
               "aprobacion": {"codigo": "aprobacion_memorias", "etapa_tipo": "memorias_calculo", "...": "nodo acto"}},
  "obras": {"codigo": "obras", "etapa_tipo": "recibo_satisfaccion_obras",
            "datos": {"informe_usuario_id": null, "radicado": null, "fecha_radicado": null,
                      "doc_informe_usuario_id": null},
            "informe": {"etapa_tipo": "informe_usuario", "...": "nodo radicado"},
            "concepto": {"tipo": "obras"}, "requerimiento": {"ambito": "obras"},
            "nuevo_informe": {"etapa_tipo": "informe_usuario"}, "concepto_segundo": {"tipo": "obras_segundo"},
            "aprobacion": {"codigo": "aprobacion_obras"}},
  "terceros": [{"id": 16, "involucrado_id": 502, "tipo_vinculo": "TERCERO_INTERVINIENTE",
                "involucrado": {"id": 502, "nombre": "Opositor", "...": "app-involved"},
                "representante_id": null, "acto_admin_id": null, "version": 1,
                "codigo": "tercero", "etapa_tipo": "expediente_involucrado",
                "encargado": null, "proceso": null, "acto": null, "anexos": [],
                "acciones_disponibles": ["editar_representante", "asignarme", "desvincular", "gestionar_anexos"]}]
}
```

**Forma de cada nodo** (todos traen las mismas claves; las que no aplican van `null` / `[]`):
`codigo`, `etiqueta`, `etapa_tipo` (tabla: sirve para anexos y para
`/revision-documentos/por-etapa/{etapa_tipo}/{id}`), `id`, `version` (para los PUT),
`existe`, `habilitada` (existe o se puede crear), `motivos_bloqueo` (textos de §6 cuando
no está habilitada), `encargado` / `tecnico` (`{id, nombre}`), `datos`, `proceso`
(resumen de B o `null`), `acto` (forma de `GET /actos/administrativos/{id}` sin
notificables, con las `acciones_disponibles` del acto), `anexos`, `acciones_disponibles`.
Los nodos de concepto traen `tipo` y `campos` (definición de los datos que pide ese
tipo de concepto, ver C.4 «Campos del concepto»; viene aunque el concepto no exista,
para el cargue directo); los de requerimiento, `ambito`.

- `etapa_actual`: la etapa MÁS avanzada que existe en el orden del plan
  (`admite < concepto < requerimiento < decision < memorias < obras`), o `null`.
- `aprobacion` (memorias/obras): el acto vive en la misma fila; `existe` = ya hay
  encargado; `id` = id de la fila de memorias/obras.

**Códigos de `acciones_disponibles`** (estables; el front solo pinta botones):

| Código | Dónde | Endpoint |
|---|---|---|
| `asignarme` | nodos de acto y terceros | `.../asignarme` (C.3–C.8, C.10) |
| `subir_version` | encargado/técnico en `pendiente_carga` / `rechazado` | B `/revision-documentos/{proceso_id}/versiones` |
| `revisar` | revisor con turno | B `/revision-documentos/{proceso_id}/revisiones` |
| `cargar_version_final` | encargado/técnico en `aprobado_firma` | `.../version-final` |
| `seleccionar_tecnico` | nodos de concepto sin técnico (no etapa 2) | C.4 |
| `cargar_oficio_alcaldia`, `cargar_fijacion_aviso`, `cargar_constancia_fijacion` | admite (tras el acto) | C.3 `PUT .../admite/documentos` |
| `registrar_respuesta` | requerimiento etapa 3 (tras el acto) | C.5 |
| `registrar_ejecutoria` | decisión (tras el acto) | C.6 |
| `crear_recurso` | `decision.recurso` | C.6 |
| `registrar_planos`, `registrar_subsanacion` | memorias | C.7 |
| `registrar_informe_usuario`, `registrar_nuevo_informe` | obras | C.8 |
| `vincular_tercero` (raíz), `editar_representante`, `desvincular` | terceros | C.10 |
| `gestionar_anexos` | cualquier nodo existente (gestión) | C.11 |
| `super_cargar` | todos los nodos (solo super gestión) | C.9 |

### C.3 Etapa 1 · Auto que admite

| Método | Ruta | Permiso | Body |
|---|---|---|---|
| POST | `/etapas/{exp}/admite/asignarme` | gestión | — |
| POST | `/etapas/{exp}/admite/version-final` | encargado | `ActoFinal` + `tecnico_id` (con `recurso_tecnico`, V3) + `fecha_visita_tecnica` (V5) |
| PUT | `/etapas/{exp}/admite/documentos` | encargado (o super) | `{version, doc_oficio_alcaldia_id?, doc_fijacion_aviso_id?, doc_constancia_fijacion_aviso_id?}` (al menos uno; reemplaza) |

`version-final` crea el acto `AUTO_ADMITE` y **nace la etapa 2**: fila `concepto_tecnico`
con técnico + fecha de visita y su proceso `CONCEPTO_ETAPA2` (encargado = técnico, que
recibe aviso). `documentos` solo después del acto.

### C.4 Conceptos técnicos (`tipo` = `etapa2|adicional|memorias|subsanacion|obras|obras_segundo`)

| Método | Ruta | Permiso | Body |
|---|---|---|---|
| GET | `/etapas/tecnicos` | gestión | → `[{id, nombre, correo}]` (usuarios con `recurso_tecnico`) |
| GET | `/etapas/abogados` | gestión | → `[{id, nombre, correo}]` (usuarios con `recurso_gestionar`; encargado en super gestión, C.9) |
| POST | `/etapas/{exp}/conceptos/{tipo}/tecnico` | gestión; `adicional`: encargado del requerimiento | `{tecnico_id}` (no aplica a `etapa2`) |
| POST | `/etapas/{exp}/conceptos/{tipo}/version-final` | **técnico seleccionado** (`recurso_tecnico`) | `ConceptoFinal` |
| GET | `/etapas/conceptos/{concepto_id}` | técnico seleccionado o lectura | — |
| POST | `/etapas/conceptos/{concepto_id}/version-final` | **técnico seleccionado** | `ConceptoFinal` |

`ConceptoFinal`: `{file_id, fecha_aceptacion (fecha del concepto = firma), fecha_visita_tecnica?,
caudal_fuente?, caudal_disponible?, caudal_otorgado?, num_usuarios?, cumple?}`. Obligatorios por tipo:
`etapa2`: los 3 caudales + `num_usuarios`; `adicional`: ninguno extra (caudales opcionales,
`TODO(negocio)`); `memorias` / `subsanacion`: `cumple`; `obras` / `obras_segundo`: `cumple` +
`fecha_visita_tecnica` (la diligencia el técnico). Los campos que no aplican al tipo se ignoran.

**Campos del concepto** (una sola fuente: `CAMPOS_CONCEPTO` / `definicion_campos_concepto`
en `services/etapas.py`). Vienen en `campos` del nodo de concepto del árbol (C.2) y de
`GET /etapas/conceptos/{id}`; el front arma con ellos el formulario de versión final, el
de Mis informes y el del cargue directo (no guarda copia):

```json
{"obligatorios": ["file_id", "fecha_aceptacion", "cumple", "fecha_visita_tecnica"],
 "opcionales": [],
 "campos": [{"campo": "fecha_aceptacion", "tipo": "fecha", "etiqueta": "Fecha del concepto (firma)", "obligatorio": true},
            {"campo": "cumple", "tipo": "si_no", "etiqueta": "¿Cumple?", "obligatorio": true},
            {"campo": "fecha_visita_tecnica", "tipo": "fecha", "etiqueta": "Fecha de visita técnica", "obligatorio": true}]}
```

`obligatorios` / `opcionales` incluyen `file_id` (PDF firmado); `campos` son solo los
datos (sin el archivo), en orden de pantalla. `tipo`: `fecha` | `decimal` | `entero` | `si_no`.

El técnico elegido (`tecnico_id` de `.../tecnico`, también cuando lo elige super gestión)
debe tener `recurso_tecnico` → si no, `400` "El usuario elegido no tiene el permiso de
técnico (recurso_tecnico) (V3)".

Condición para seleccionar técnico: `adicional` tras la respuesta del usuario al
requerimiento; `memorias` tras el radicado de planos; `subsanacion` tras la subsanación;
`obras` tras el informe; `obras_segundo` tras el nuevo informe.

**Técnico desde Mis informes** (no entra a Gestionar): la fila de `GET /mis-documentos`
con `etapa_tipo = "concepto_tecnico"` trae `etapa_ref_id` = id del concepto. El front
llama `GET /etapas/conceptos/{etapa_ref_id}`:

```json
{"ok": true, "data": {
  "id": 9, "version": 1, "tipo": "etapa2", "etiqueta": "Etapa 2 · Concepto técnico",
  "expediente": {"id": 3, "expediente": "CA 012-26", "radicado": "2026ER00012",
                 "nombre_predio": "La Esperanza", "nombre_fuente": "Juancho Castro"},
  "tecnico": {"id": 32, "nombre": "Ana"},
  "datos": {"fecha_visita_tecnica": "2026-05-02", "fecha_aceptacion": null, "caudal_fuente": null,
            "caudal_disponible": null, "caudal_otorgado": null, "num_usuarios": null,
            "cumple": null, "doc_concepto_tecnico_id": null},
  "campos": {"obligatorios": ["file_id", "fecha_aceptacion", "caudal_fuente", "caudal_disponible",
                              "caudal_otorgado", "num_usuarios"], "opcionales": [],
             "campos": [{"campo": "fecha_aceptacion", "tipo": "fecha", "...": "ver «Campos del concepto»"}]},
  "proceso": {"proceso_id": 21, "estado_proceso": {"codigo": "aprobado_firma", "...": "..."}, "...": "resumen de B"},
  "acciones_disponibles": ["cargar_version_final"]
}}
```

Con `cargar_version_final` envía `POST /etapas/conceptos/{id}/version-final`
(`acciones_disponibles` puede ser `subir_version`: las versiones en proyección se suben
por B, `/revision-documentos/{proceso_id}/versiones`). Otro técnico → 403.

### C.5 Requerimientos (`ambito` = `etapa3|memorias|obras`)

| Método | Ruta | Permiso | Body |
|---|---|---|---|
| POST | `/etapas/{exp}/requerimientos/{ambito}/asignarme` | gestión | — |
| POST | `/etapas/{exp}/requerimientos/{ambito}/version-final` | encargado | `ActoFinal` |
| PUT | `/etapas/{exp}/requerimientos/etapa3/respuesta` | encargado (o super) | `{version, radicado_oficio_entrada (≤15), fecha_oficio_entrada, doc_oficio_entrada_id}` |

`etapa3`: V4 + V6 (concepto de la etapa 2 cargado). `memorias` / `obras`: V11 (el concepto
de memorias / de obras dice `cumple = false`). La respuesta va después del acto.

### C.6 Etapa 4 · Decisión y recurso de reposición

| Método | Ruta | Permiso | Body |
|---|---|---|---|
| POST | `/etapas/{exp}/decision/asignarme` | gestión | — (V4 + V7: constancia de fijación; no requiere concepto) |
| POST | `/etapas/{exp}/decision/version-final` | encargado | `ActoFinal` + `decision` (`OTORGADA|NEGADA|DESISTIDA`) + `requiere_memorias` (obligatorio si OTORGADA; V8) |
| PUT | `/etapas/{exp}/decision/ejecutoria` | encargado (o super) | `{version, fecha_ejecutoria}` (`null` la borra) |
| POST | `/etapas/{exp}/recurso` | gestión | `Radicado` → `201` (V13: decisión notificada) |
| POST | `/etapas/{exp}/recurso/asignarme` | gestión | — (UPDATE atómico) |
| POST | `/etapas/{exp}/recurso/version-final` | encargado | `ActoFinal` + `resultado` (`REPONE|CONFIRMA|MODIFICA|ADICIONA`) |

`Radicado`: `{radicado (≤15), fecha_radicado, file_id}`. La decisión se toma una sola vez
(segunda carga → 409). `fecha_ejecutoria` la diligencia el abogado: `TODO(negocio)` (no
hay calendario de días hábiles). "Notificada" = regla provisional de B (≥1 notificación
y todas exitosas).

### C.7 Etapa 5 · Memorias de cálculo

| Método | Ruta | Permiso | Body |
|---|---|---|---|
| POST | `/etapas/{exp}/memorias` | gestión | `Radicado` (planos) → `201` (V9) |
| POST | `/etapas/{exp}/memorias/subsanacion` | gestión | `Radicado` (planos ajustados) → `201` (tras el requerimiento firmado) |
| POST | `/etapas/{exp}/memorias/aprobacion/asignarme` | gestión | — (V12: último concepto `cumple = true`) |
| POST | `/etapas/{exp}/memorias/aprobacion/version-final` | encargado | `ActoFinal` (`APRUEBA_MEMORIAS`) |

Conceptos: C.4 `memorias` / `subsanacion`; requerimiento: C.5 `memorias`.

### C.8 Etapa 6 · Recibo a satisfacción de obras

| Método | Ruta | Permiso | Body |
|---|---|---|---|
| POST | `/etapas/{exp}/obras` | gestión | `Radicado` (informe del usuario) → `201` (V10) |
| POST | `/etapas/{exp}/obras/nuevo-informe` | gestión | `Radicado` → `201` (tras el requerimiento firmado) |
| POST | `/etapas/{exp}/obras/aprobacion/asignarme` | gestión | — (V12) |
| POST | `/etapas/{exp}/obras/aprobacion/version-final` | encargado | `ActoFinal` (`APRUEBA_OBRAS`) |

Conceptos: C.4 `obras` / `obras_segundo`; requerimiento: C.5 `obras`.

### C.9 Super gestión — `/recurso/super-gestion` (solo `recurso_super_gestion`)

Cargue directo / histórico sin revisión, sin "Asignarme" y sin validaciones §6; las
restricciones de BD sí aplican (campos obligatorios para crear → 400; duplicados → 409).
Todos `POST`, body JSON. Si la fila no existe se crea; si existe se actualizan solo los
campos enviados (no nulos). `version` es opcional (si llega y no coincide → 409).
`acto` = `{numerado, fecha_numerado, file_id}`: crea y enlaza el acto si la fila no tiene
(si ya tiene → 409; se corrige con `PUT /actos/administrativos/{id}`) y **cierra** el
proceso de revisión abierto. `encargado_acto_id` es **opcional** (el front lo elige de
`GET /etapas/abogados`): al crear la fila sin él, la etapa queda **sin encargado**
(NULL; expedientes antiguos): no se crea proceso de revisión, el árbol no ofrece
"Asignarme" sobre esa fila y solo super gestión gestiona su acto. Al actualizar, si no
llega se conserva el actual; si llega otro y la etapa no tiene acto, el proceso
abierto pasa a su nombre. **La persona elegida sí se valida** (aunque el resto del
cargue omita §6): `encargado_acto_id` debe tener `recurso_gestionar` y `tecnico_id` /
`tecnico_encargado_id`, `recurso_tecnico`; si no → `400` ("El usuario elegido no tiene el
permiso de ..."). Solo se valida cuando el valor cambia respecto al que ya tenía la fila. (`acto_admite`/`requerimiento`/`decision` admiten NULL: desviación del DBML,
DISENO_TECNICO §2.)

| Ruta | Body |
|---|---|
| `/super-gestion/{exp}/admite` | `{version?, encargado_acto_id?, acto?, doc_oficio_alcaldia_id?, doc_fijacion_aviso_id?, doc_constancia_fijacion_aviso_id?, tecnico_id?, fecha_visita_tecnica?}` (con `tecnico_id` nace el concepto de etapa 2 con su proceso) |
| `/super-gestion/{exp}/conceptos/{tipo}` | `{version?, tecnico_encargado_id (para crear), fecha_visita_tecnica?, fecha_aceptacion?, caudales?, num_usuarios?, cumple?, file_id?}` (`file_id` = concepto firmado; cierra su proceso). El padre debe existir |
| `/super-gestion/{exp}/requerimientos/{ambito}` | `{version?, encargado_acto_id?, acto?, radicado_oficio_entrada?, fecha_oficio_entrada?, doc_oficio_entrada_id?}` (la respuesta solo aplica a `etapa3`) |
| `/super-gestion/{exp}/decision` | `{version?, encargado_acto_id?, acto?, decision?, requiere_memorias?, fecha_ejecutoria?}` |
| `/super-gestion/{exp}/recurso` | `{version?, radicado?, fecha_radicado?, file_id?, encargado_acto_id?, acto?, resultado?}` (requiere decisión) |
| `/super-gestion/{exp}/memorias` | `{version?, radicado?, fecha_radicado?, file_id? (planos), encargado_acto_id?, acto?}` |
| `/super-gestion/{exp}/memorias/subsanacion` | `{radicado?, fecha_radicado?, file_id?}` |
| `/super-gestion/{exp}/obras` | `{version?, radicado?, fecha_radicado?, file_id? (informe), encargado_acto_id?, acto?}` |
| `/super-gestion/{exp}/obras/nuevo-informe` | `{radicado?, fecha_radicado?, file_id?}` |
| `/super-gestion/terceros/{vinculo_id}/acto` | `{acto}` |

Respuesta: `{"ok": true, "message", "data": {id, version, acto_id?}}`.

### C.10 Tercero interviniente — `/recurso/terceros`

| Método | Ruta | Permiso | Body / respuesta |
|---|---|---|---|
| GET | `/terceros/expediente/{exp}` | lectura | lista con la forma de `etapas.terceros` |
| POST | `/terceros` | gestión | `{expediente_id, involucrado_id, representante_id?}` → `201` + vínculo (V14; 409 si ya está vinculado) |
| PATCH | `/terceros/{vinculo_id}/representante` | gestión | `{representante_id, version}` |
| DELETE | `/terceros/{vinculo_id}?version=N` | gestión | 409 si tiene acto, notificaciones o el acto en proyección |
| POST | `/terceros/{vinculo_id}/asignarme` | gestión | crea el proceso `RECONOCE_TERCERO` (encargado = quien se asigna) |
| POST | `/terceros/{vinculo_id}/version-final` | encargado | `ActoFinal` → acto en `expediente_involucrado.acto_admin_id` |

No exige auto admite (el tercero aparece "en cualquier momento"). Se notifica con
`/actos/notificaciones` (B).

### C.11 Documentos anexos — `/recurso/documentos-anexos`

`etapa_tipo` ∈ `acto_admite, concepto_tecnico, requerimiento,
decision, recurso_reposicion, memorias_calculo, subsanacion, recibo_satisfaccion_obras,
informe_usuario` (= `etapa_tipo` del nodo); la fila debe pertenecer al expediente (si no,
404). PDF obligatorio. Los carga el abogado (gestión). Cada nodo trae SUS anexos:
`obras.informe` y `obras.nuevo_informe` (`informe_usuario`) y `memorias.subsanacion`
(`subsanacion`) tienen los suyos, aparte de los de la fila de obras / memorias, y
ofrecen `gestionar_anexos`.

| Método | Ruta | Body |
|---|---|---|
| GET | `/documentos-anexos?expediente_id=&etapa_tipo=&etapa_ref_id=` (lectura) | → `[{id, etapa_tipo, etapa_ref_id, nombre, documento_anexo_id, fecha_subida}]` |
| POST | `/documentos-anexos` | `{expediente_id, etapa_tipo, etapa_ref_id, nombre (≤100), documento_anexo_id}` → `201` |
| PUT | `/documentos-anexos/{id}` | `{expediente_id, nombre, documento_anexo_id?}`: cambia el nombre y, si llega `documento_anexo_id` distinto, reemplaza el PDF (validado; +1 uso al nuevo antes del commit, −1 al anterior después). La tabla no tiene `version` |
| DELETE | `/documentos-anexos/{id}?expediente_id=` | — |

### C.12 Contexto de etapa en Mis informes y en el detalle del proceso

Las filas de `GET /mis-documentos` y el detalle `GET /revision-documentos/{id}` traen además:

- `etapa_padre`: etapa del plan (pestaña) a la que pertenece el documento:
  `acto_admite`, `concepto_tecnico` (etapa 2), `requerimiento` (etapa 3, incluido su
  concepto adicional), `decision` (incluido el recurso), `memorias_calculo`,
  `recibo_satisfaccion_obras`, `tercero_interviniente`.
- `etapa_padre_etiqueta`: p. ej. `"Etapa 5 · Memorias de cálculo"`.
- `sub_proceso`: `auto_admite`, `concepto_etapa2`, `concepto_adicional`,
  `requerimiento_etapa3` | `requerimiento_memorias` | `requerimiento_obras`, `decision`,
  `recurso`, `concepto_memorias`, `concepto_subsanacion`, `concepto_obras`,
  `concepto_obras_segundo`, `aprobacion`, `reconoce_tercero`.
