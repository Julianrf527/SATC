# MANUAL DE PERMISOS — SISTEMA SATC

**Sistema de Apoyo Técnico Corpochivor**  
**Versión:** develop  
**Fecha:** 16 de junio de 2026  
**Audiencia:** Administradores del sistema, coordinadores, soporte técnico

---

## 1. INTRODUCCIÓN

El sistema SATC implementa un modelo de control de acceso basado en permisos (PBAC — Permission-Based Access Control). Cada usuario tiene un **rol**, y cada rol tiene una lista de **permisos** asignados. Los permisos controlan simultáneamente dos cosas:

1. **Visibilidad en la interfaz:** qué categorías y pestañas aparecen en el menú lateral
2. **Acceso a la API:** qué operaciones puede ejecutar en el servidor

No existe forma de saltarse este control: aunque un usuario conociera la URL directa de una función, el backend rechaza la solicitud con HTTP 403 si no tiene el permiso correspondiente.

### 1.1 Cómo funciona técnicamente

El token de sesión incluye la lista completa de permisos del usuario. El API Gateway inyecta esta lista en cada solicitud al microservicio. El microservicio verifica el permiso antes de ejecutar cualquier operación sensible. En el frontend, el componente `RequirePermission` redirige a inicio (`/`) si el usuario navega a una ruta para la que no tiene permiso.

---

## 2. CATÁLOGO COMPLETO DE PERMISOS

El sistema tiene **21 permisos** organizados en 6 categorías. Los permisos marcados con 🔇 no generan elemento de menú — actúan únicamente en el backend.

| #   | Nombre del permiso            | Categoría      | Ruta de menú                |
| --- | ----------------------------- | -------------- | --------------------------- |
| 1   | `admin_roles`                 | Administración | `/user/role`                |
| 2   | `admin_crear_usuarios`        | Administración | `/user/add`                 |
| 3   | `admin_gestionar_usuarios`    | Administración | `/user/manage`              |
| 4   | `expediente_gestionar`        | Expedientes    | `/file/manage`              |
| 5   | `expediente_consultar`        | Expedientes    | `/file/consult`             |
| 6   | `expediente_alertas`          | Expedientes    | `/file/alerts`              |
| 7   | `expediente_asignar`          | Expedientes    | `/file/assign_manage`       |
| 8   | `infraccion_gestionar`        | Infracciones   | `/infraction/manage`        |
| 9   | `infraccion_consultar`        | Infracciones   | `/infraction/consult`       |
| 10  | `infraccion_alertas`          | Infracciones   | `/infraction/alerts`        |
| 11  | `infraccion_asignar`          | Infracciones   | `/infraction/assign_manage` |
| 12  | `infraccion_asignar_informes` | Infracciones   | `/infraction/reports`       |
| 13  | `documento_gestionar`         | Documentos     | `/document/manage`          |
| 14  | `documento_crear` 🔇          | Documentos     | _(sin menú)_                |
| 15  | `documento_revisar` 🔇        | Documentos     | _(sin menú)_                |
| 16  | `involucrado_gestionar`       | Involucrados   | `/involved/manage`          |
| 17  | `auditoria_usuarios`          | Auditoría      | `/audit/users`              |
| 18  | `auditoria_expedientes`       | Auditoría      | `/audit/files`              |
| 19  | `auditoria_involucrados`      | Auditoría      | `/audit/involved`           |
| 20  | `auditoria_infracciones`      | Auditoría      | `/audit/infractions`        |
| 21  | `subir_informes` 🔇           | _(backend)_    | _(sin menú)_                |

---

## 3. MENÚ LATERAL — COMPORTAMIENTO DINÁMICO

El menú lateral del sistema es completamente dinámico. Se construye en tiempo real a partir de los permisos del usuario autenticado. Si un usuario no tiene ningún permiso de una categoría, esa categoría no aparece en el menú.

### 3.1 Categorías del menú

| Categoría          | Ícono                | Se muestra cuando...                                                                                                                                        |
| ------------------ | -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Administración** | Libreta de contactos | El usuario tiene al menos uno de: `admin_roles`, `admin_crear_usuarios`, `admin_gestionar_usuarios`                                                         |
| **Expedientes**    | Archivo              | El usuario tiene al menos uno de: `expediente_gestionar`, `expediente_consultar`, `expediente_alertas`, `expediente_asignar`                                |
| **Infracciones**   | Martillo             | El usuario tiene al menos uno de: `infraccion_gestionar`, `infraccion_consultar`, `infraccion_alertas`, `infraccion_asignar`, `infraccion_asignar_informes` |
| **Documentos**     | Libro                | El usuario tiene `documento_gestionar`                                                                                                                      |
| **Involucrados**   | Círculo de usuario   | El usuario tiene `involucrado_gestionar`                                                                                                                    |
| **Auditoría**      | Calendario           | El usuario tiene al menos uno de: `auditoria_usuarios`, `auditoria_expedientes`, `auditoria_involucrados`, `auditoria_infracciones`                         |

### 3.2 Orden de subelementos dentro de cada categoría

**Expedientes:** Gestionar → Consultar → Alertas → Asignar  
**Infracciones:** Gestionar → Consultar → Alertas → Asignar → Asignar Informes

---

## 4. DESCRIPCIÓN DETALLADA DE CADA PERMISO

---

### CATEGORÍA: ADMINISTRACIÓN

---

#### `admin_roles` — Administración de roles y permisos

**Ruta:** `/user/role`  
**Microservicio:** `app-users`

**Qué desbloquea:**

- **Pestaña "Roles"** en el menú de Administración
- Ver la lista completa de roles existentes en el sistema
- Crear nuevos roles con nombre personalizado
- Editar roles existentes (cambiar nombre)
- Asignar y quitar permisos a un rol usando el formulario de asignación
- Eliminar roles (siempre que no tengan usuarios asignados)
- Ver qué permisos tiene cada rol

**Restricciones:**

- No puede crear o modificar usuarios directamente
- Los cambios en permisos de un rol afectan a todos los usuarios que tengan ese rol asignado

---

#### `admin_crear_usuarios` — Creación de usuarios

**Ruta:** `/user/add`  
**Microservicio:** `app-users`

**Qué desbloquea:**

- **Pestaña "Agregar usuario"** en el menú de Administración
- Formulario para registrar un nuevo usuario en el sistema
- Campos disponibles: número de documento, nombre completo, correo electrónico, contraseña inicial, rol asignado
- El nuevo usuario queda activo inmediatamente

**Restricciones:**

- Solo puede asignar roles que ya existen — no puede crear roles desde aquí
- No puede ver ni editar usuarios ya creados (eso requiere `admin_gestionar_usuarios`)

---

#### `admin_gestionar_usuarios` — Gestión de usuarios existentes

**Ruta:** `/user/manage`  
**Microservicio:** `app-users`

**Qué desbloquea:**

- **Pestaña "Gestionar usuarios"** en el menú de Administración
- Ver la lista completa de usuarios del sistema con su estado (activo/inactivo)
- Buscar usuarios por nombre, documento o correo
- Editar datos de un usuario (nombre, correo, rol)
- Activar o desactivar usuarios (bloquear acceso sin eliminar)
- Cambiar el rol de un usuario

**Restricciones:**

- No puede eliminar usuarios de forma permanente (solo desactivar)
- No puede crear usuarios nuevos (eso requiere `admin_crear_usuarios`)

---

### CATEGORÍA: EXPEDIENTES (Proceso sancionatorio)

---

#### `expediente_gestionar` — Gestión completa de expedientes sancionatorios

**Ruta:** `/file/manage`  
**Microservicio:** `app-sanctioning`

**Qué desbloquea:**

- **Pestaña "Gestionar"** en el menú de Expedientes
- Lista completa de todos los expedientes sancionatorios del sistema con filtros
- Crear un nuevo expediente sancionatorio (radicado, fecha, datos del caso)
- Ver el detalle completo del expediente: datos generales, quejoso, recursos afectados, involucrados, etapas procesales, actos administrativos, comunicaciones
- Editar datos del expediente (cuando el usuario es el **encargado asignado**)
- Registrar etapas procesales:
  - Indagación preliminar
  - Medida preventiva
  - Inicio del proceso sancionatorio
  - Formulación de cargos
  - Apertura/cierre de etapa probatoria
  - Decisión de fondo
  - Ejecución de la sanción
  - Cesación
- Crear y editar actos administrativos
- Registrar comunicaciones y notificaciones
- Descargar el PDF unificado del expediente
- Aparece como **opción disponible para ser asignado como encargado** cuando un usuario con `expediente_asignar` hace una asignación

**Restricciones importantes:**

- Las operaciones de **escritura** (editar, crear etapas, actos) solo funcionan si el usuario es el **abogado responsable (encargado)** del expediente. Ver un expediente de otro abogado es posible, modificarlo no.
- Requiere ser asignado como encargado por alguien con `expediente_asignar`

---

#### `expediente_consultar` — Consulta de expedientes sancionatorios (solo lectura)

**Ruta:** `/file/consult`  
**Microservicio:** `app-sanctioning`

**Qué desbloquea:**

- **Pestaña "Consultar"** en el menú de Expedientes
- Lista de todos los expedientes con filtros (radicado, fecha, estado, encargado)
- Ver el detalle completo de cualquier expediente en modo solo lectura
- Ver todas las etapas, actos, comunicaciones y documentos adjuntos
- Descargar el PDF del expediente

**Restricciones:**

- **No puede crear, editar ni registrar ninguna etapa o acto**
- Solo lectura de toda la información
- Diferencia con `expediente_gestionar`: este permiso no da acceso a formularios de edición

---

#### `expediente_alertas` — Alertas de expedientes

**Ruta:** `/file/alerts`  
**Microservicio:** `app-sanctioning`

**Qué desbloquea:**

- **Pestaña "Alertas"** en el menú de Expedientes
- Panel de alertas automáticas calculadas sobre los expedientes
- Ver expedientes próximos a vencer términos procesales
- Ver expedientes con términos ya vencidos
- Indicadores de urgencia por colores según criticidad del vencimiento

**Restricciones:**

- Solo lectura — no puede tomar acciones desde esta pantalla
- Las alertas se calculan automáticamente según las fechas del proceso

---

#### `expediente_asignar` — Asignación de encargados en expedientes

**Ruta:** `/file/assign_manage`  
**Microservicio:** `app-sanctioning`

**Qué desbloquea:**

- **Pestaña "Asignar"** en el menú de Expedientes
- Ver todos los expedientes con su encargado actual
- Cambiar el encargado de un expediente individual
- **Asignación masiva (bulk):** seleccionar múltiples expedientes y cambiar su encargado con una sola acción
- Ver la lista de usuarios disponibles para ser encargados (usuarios con `expediente_gestionar`)

**Restricciones:**

- Solo puede asignar como encargados a usuarios que tienen `expediente_gestionar`
- No puede ver ni editar el contenido de los expedientes desde esta vista

---

### CATEGORÍA: INFRACCIONES

---

#### `infraccion_gestionar` — Gestión completa de infracciones

**Ruta:** `/infraction/manage`  
**Microservicio:** `app-infraction`

**Qué desbloquea:**

- **Pestaña "Gestionar"** en el menú de Infracciones
- Lista completa de todos los expedientes de infracción con filtros
- Crear un nuevo expediente de infracción
- Ver el detalle completo del expediente de infracción
- Registrar y editar etapas:
  - Respuesta al emplazamiento
  - Medida preventiva
  - Acto de cierre
- Registrar actos administrativos de infracción
- Subir documentos y archivos relacionados al expediente
- Descargar el PDF unificado del expediente
- Aparece como **opción disponible para ser asignado como encargado** cuando un usuario con `infraccion_asignar` hace una asignación
- Ver los involucrados asociados al expediente

**Restricciones:**

- Las operaciones de escritura solo están disponibles si el usuario es el encargado del expediente
- No puede gestionar el flujo de informes técnicos (eso requiere `infraccion_asignar_informes`)

---

#### `infraccion_consultar` — Consulta de infracciones (solo lectura)

**Ruta:** `/infraction/consult`  
**Microservicio:** `app-infraction`

**Qué desbloquea:**

- **Pestaña "Consultar"** en el menú de Infracciones
- Lista de todos los expedientes de infracción en modo lectura
- Ver el detalle completo de cualquier expediente de infracción
- Consultar los informes técnicos asociados (VISITA, CONCEPTO, etc.)
- Descargar el PDF del expediente (sin necesidad de ser el encargado)

**Restricciones:**

- Solo lectura — sin acceso a formularios de edición ni registro de etapas

---

#### `infraccion_alertas` — Alertas de infracciones

**Ruta:** `/infraction/alerts`  
**Microservicio:** `app-infraction`

**Qué desbloquea:**

- **Pestaña "Alertas"** en el menú de Infracciones
- Panel de alertas de vencimiento de términos para expedientes de infracción
- Indicadores de urgencia con fechas límite

---

#### `infraccion_asignar` — Asignación de encargados en infracciones

**Ruta:** `/infraction/assign_manage`  
**Microservicio:** `app-infraction`

**Qué desbloquea:**

- **Pestaña "Asignar"** en el menú de Infracciones
- Ver todos los expedientes de infracción con su encargado actual
- Cambiar el encargado de un expediente individual
- **Asignación masiva (bulk):** múltiples expedientes, un solo encargado nuevo
- Lista de usuarios disponibles para asignar (usuarios con `infraccion_gestionar`)

---

#### `infraccion_asignar_informes` — Gestión del flujo de informes técnicos

**Ruta:** `/infraction/reports`  
**Microservicio:** `app-infraction`

**Qué desbloquea:**

- **Pestaña "Asignar Informes"** en el menú de Infracciones
- Ver la lista de expedientes que requieren un informe técnico
- Ver los profesionales disponibles para recibir la asignación (usuarios con `subir_informes`)
- Asignar un informe técnico (VISITA, CONCEPTO, etc.) a un profesional específico
- Reasignar o cancelar una asignación existente
- Ver el estado de cada informe: pendiente, en proceso, entregado
- Confirmar la recepción del informe entregado por el profesional

**Relación con `subir_informes`:** Este permiso es el del coordinador que **asigna**. El profesional que **sube** el informe tiene `subir_informes`. Son dos roles distintos en el mismo flujo.

---

### CATEGORÍA: DOCUMENTOS

Los documentos tienen un modelo de tres permisos que forman un flujo de trabajo. Un usuario puede tener uno, dos, o los tres simultáneamente.

---

#### `documento_gestionar` — Acceso al módulo de documentos

**Ruta:** `/document/manage`  
**Microservicio:** `app-docs`

**Qué desbloquea:**

- **Categoría "Documentos"** visible en el menú lateral
- Acceso a la página de documentos

**Importante:** Este permiso solo controla la visibilidad del menú y la entrada a la página. Las acciones reales dentro del módulo (listar, crear, revisar) requieren `documento_crear` o `documento_revisar`. Un usuario con solo `documento_gestionar` y ninguno de los otros dos verá la página pero recibirá error 403 al intentar cargar la lista de documentos.

**Recomendación:** Asignar siempre junto con `documento_crear` o `documento_revisar`.

---

#### `documento_crear` 🔇 — Creación y carga de documentos

**Ruta de menú:** _(ninguna — permiso de backend)_  
**Microservicio:** `app-docs`

**Qué desbloquea:**

- Crear un nuevo documento en el sistema
- Completar formulario con nombre, descripción y archivo adjunto
- Cargar el archivo a MinIO con verificación antivirus (ClamAV)
- Seleccionar revisores para el documento (de la lista de usuarios con `documento_revisar`)
- Ver todos los documentos propios y su estado de revisión
- Subir nuevas versiones de un documento que fue devuelto
- Recibir notificaciones cuando un revisor aprueba o devuelve el documento

**Flujo típico:**

1. Crea el documento y lo sube → estado: **En revisión**
2. Revisor lo aprueba → estado: **Aprobado** (notificación al creador)
3. Revisor lo devuelve → estado: **Devuelto** (notificación al creador)
4. Creador sube nueva versión → vuelve a **En revisión**

---

#### `documento_revisar` 🔇 — Revisión y aprobación de documentos

**Ruta de menú:** _(ninguna — permiso de backend)_  
**Microservicio:** `app-docs`

**Qué desbloquea:**

- Aparecer en la lista de revisores disponibles al crear un documento
- Ver todos los documentos asignados para revisión
- Descargar el archivo del documento para revisarlo
- Aprobar un documento (cambia estado a **Aprobado**)
- Devolver un documento con comentarios (cambia estado a **Devuelto**)
- Recibir notificaciones cuando se asigna un documento para revisión
- Ver el historial de versiones y revisiones anteriores

---

### CATEGORÍA: INVOLUCRADOS

---

#### `involucrado_gestionar` — Gestión de involucrados

**Ruta:** `/involved/manage`  
**Microservicio:** `app-involved`

**Qué desbloquea:**

- **Categoría "Involucrados"** en el menú lateral con pestaña "Gestionar"
- Ver la lista completa de personas involucradas registradas en el sistema
- Buscar una persona por tipo de documento (CC, CE, NIT) y número
- Crear un nuevo registro de persona involucrada
- Ver el historial de en qué expedientes aparece una persona
- Editar datos de una persona (actualizar información de contacto)

---

### CATEGORÍA: AUDITORÍA

Los permisos de auditoría son de **solo lectura** — ninguno permite modificar datos. Son registros históricos de actividad generados automáticamente por el sistema.

---

#### `auditoria_usuarios` — Logs de actividad de usuarios

**Ruta:** `/audit/users`  
**Microservicio:** `app-users`

**Qué desbloquea:**

- **Subelemento "Usuarios"** en la categoría Auditoría
- Ver el registro de todas las acciones de administración de usuarios: logins, cambios de contraseña, creación/edición de usuarios, cambios de roles
- Filtrar por usuario, tipo de evento y rango de fechas
- Ver IP de origen de cada acción

---

#### `auditoria_expedientes` — Logs de expedientes sancionatorios

**Ruta:** `/audit/files`  
**Microservicio:** `app-sanctioning`

**Qué desbloquea:**

- **Subelemento "Expedientes"** en la categoría Auditoría
- Ver el registro completo de todas las acciones sobre expedientes sancionatorios: creación, edición, cambio de encargado, registro de etapas, descargas
- Filtrar por expediente (radicado), usuario, tipo de acción y fechas
- Datos anteriores y nuevos en cada modificación (historial de cambios)

---

#### `auditoria_involucrados` — Logs de involucrados

**Ruta:** `/audit/involved`  
**Microservicio:** `app-involved`

**Qué desbloquea:**

- **Subelemento "Involucrados"** en la categoría Auditoría
- Registro de creación y modificaciones de registros de personas involucradas

---

#### `auditoria_infracciones` — Logs de expedientes de infracción

**Ruta:** `/audit/infractions`  
**Microservicio:** `app-infraction`

**Qué desbloquea:**

- **Subelemento "Infracciones"** en la categoría Auditoría
- Registro completo de acciones sobre expedientes de infracción: creación, edición, asignaciones, subida de informes, cambio de encargado
- Historial de datos antes y después de cada modificación

---

### PERMISO ESPECIAL (Backend)

---

#### `subir_informes` 🔇 — Profesional que sube informes técnicos

**Ruta de menú:** _(ninguna)_  
**Microservicio:** `app-infraction`

**Qué desbloquea:**

- El usuario **aparece en la lista de profesionales disponibles** cuando alguien con `infraccion_asignar_informes` va a asignar un informe técnico
- Recibir una asignación de informe técnico (VISITA, CONCEPTO TÉCNICO, etc.)
- Ver los informes técnicos asignados pendientes de entrega
- Subir el archivo del informe técnico completado
- Recibir notificaciones de nuevas asignaciones

**Este permiso no genera ninguna pestaña en el menú.** El profesional que lo tiene accede al sistema normalmente y ve sus asignaciones dentro de la vista de infracción, o recibe la notificación directamente.

---

## 5. FLUJOS DE TRABAJO Y PERMISOS NECESARIOS

### 5.1 Flujo sancionatorio completo

```
Coordinador (expediente_asignar)
    └─ Asigna expediente a →  Abogado (expediente_gestionar)
                                  └─ Registra etapas, actos, comunicaciones
                                  └─ Descarga PDF del expediente

Consultor (expediente_consultar)
    └─ Solo puede leer — sin editar nada

Jefe de área (auditoria_expedientes)
    └─ Ve todos los cambios históricos del expediente
```

### 5.2 Flujo de infracciones con informes técnicos

```
Coordinador de infracciones (infraccion_asignar + infraccion_asignar_informes)
    ├─ Asigna expediente a Abogado → (infraccion_gestionar)
    └─ Asigna informe técnico a Profesional → (subir_informes)

Abogado (infraccion_gestionar)
    └─ Gestiona el expediente, registra etapas

Profesional técnico (subir_informes)
    └─ Recibe asignación → sube informe técnico completado

Consultor (infraccion_consultar)
    └─ Solo lectura: consulta expedientes e informes técnicos
```

### 5.3 Flujo de documentos

```
Creador (documento_gestionar + documento_crear)
    └─ Crea documento → Asigna revisores → Espera aprobación
    └─ Si es devuelto: sube nueva versión

Revisor (documento_gestionar + documento_revisar)
    └─ Recibe notificación → Descarga → Aprueba o Devuelve con comentarios

Nota: documento_gestionar es necesario en ambos roles para ver el módulo.
```

### 5.4 Administrador completo del sistema

Un administrador que necesite acceso total requiere los 21 permisos. La forma correcta es crear un rol "admin" con todos los permisos asignados (así está configurado por defecto en el seed del sistema).

---

## 6. PERFILES DE ROL SUGERIDOS

Los siguientes perfiles son ejemplos de configuraciones típicas para distintos cargos.

### Rol: Abogado sancionatorio

| Permiso                 | Incluir |
| ----------------------- | ------- |
| `expediente_gestionar`  | ✅      |
| `expediente_consultar`  | ✅      |
| `expediente_alertas`    | ✅      |
| `involucrado_gestionar` | ✅      |
| `documento_gestionar`   | ✅      |
| `documento_crear`       | ✅      |

### Rol: Abogado lider sancionatorio

| Permiso                 | Incluir |
| ----------------------- | ------- |
| `expediente_gestionar`  | ✅      |
| `expediente_consultar`  | ✅      |
| `expediente_alertas`    | ✅      |
| `expediente_asignar`    | ✅      |
| `auditoria_expedientes` | ✅      |
| `documento_gestionar`   | ✅      |
| `documento_crear`       | ✅      |

### Rol: Lider Tecnico

| Permiso                | Incluir |
| ---------------------- | ------- |
| `infraccion_consultar` | ✅      |
| `subir_informes`       | ✅      |

### Rol: Abogado infracciones

| Permiso                       | Incluir |
| ----------------------------- | ------- |
| `infraccion_gestionar`        | ✅      |
| `infraccion_consultar`        | ✅      |
| `infraccion_alertas`          | ✅      |
| `infraccion_asignar`          | ✅      |
| `infraccion_asignar_informes` | ✅      |
| `auditoria_infracciones`      | ✅      |
| `documento_gestionar` | ✅      |
| `documento_crear`             | ✅      |

### Rol: Revisor de documentos

| Permiso               | Incluir |
| --------------------- | ------- |
| `documento_gestionar` | ✅      |
| `documento_revisar`   | ✅      |

### Rol: Administrador

Todos los 21 permisos. Rol creado automáticamente por el sistema al iniciar.

### Rol: Solo consulta (auditor externo)

| Permiso                  | Incluir |
| ------------------------ | ------- |
| `expediente_consultar`   | ✅      |
| `infraccion_consultar`   | ✅      |

---

## 7. NOTAS TÉCNICAS IMPORTANTES

### 7.1 Permisos sin menú (`documento_crear`, `documento_revisar`, `subir_informes`)

Estos tres permisos no tienen `menu_path` definido, por lo que el componente `Slider.tsx` los filtra y nunca genera una entrada de menú para ellos. Actúan exclusivamente en el backend controlando qué operaciones de API puede ejecutar el usuario.

### 7.2 Doble capa de protección en expediente_gestionar

El permiso `expediente_gestionar` otorga acceso a la vista de gestión, pero las operaciones de escritura tienen una verificación adicional: el backend comprueba que `abogado_responsable_id == user_id`. Esto significa que un abogado con `expediente_gestionar` puede ver todos los expedientes pero solo puede modificar los que tiene asignados. Esta verificación existe en `app-sanctioning` (función `_get_expediente_con_permiso`) y en `app-infraction`.

### 7.3 Efectos de revocar un permiso

Al quitar un permiso de un rol, el cambio es efectivo en la siguiente solicitud del usuario — no requiere que el usuario cierre sesión. Esto se debe a que el backend valida permisos contra la base de datos en tiempo real (no los lee del token).

### 7.4 Sesión única por usuario

El sistema permite únicamente una sesión activa por cuenta. Si un usuario inicia sesión desde un segundo dispositivo, la sesión anterior queda inválida automáticamente. Esto es un mecanismo de seguridad gestionado por Redis.

---

_Documento generado a partir del análisis del código fuente de los microservicios `app-users`, `app-sanctioning`, `app-infraction`, `app-docs`, `app-involved` y el frontend React del sistema SATC._
