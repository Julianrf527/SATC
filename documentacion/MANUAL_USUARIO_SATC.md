# Manual de Usuario - SATC

## Sistema de Administración de Trámites de Corpochivor

**Versión:** 2.0  
**Fecha:** 20 de julio de 2026  
**Elaborado por:** Julian David Rodriguez Fernandez  
**Clasificación:** Uso Interno - Gubernamental


---

## Tabla de Contenidos

1. [Introducción](#1-introducción)
2. [Acceso al Sistema](#2-acceso-al-sistema)
3. [Módulo de Expedientes Sancionatorios](#3-módulo-de-expedientes-sancionatorios)
4. [Módulo de Infracciones](#4-módulo-de-infracciones)
5. [Módulo de Gestión de Documentos](#5-módulo-de-gestión-de-documentos)
6. [Módulo de Involucrados](#6-módulo-de-involucrados)
7. [Módulo de Administración](#7-módulo-de-administración)
8. [Módulo de Auditoría](#8-módulo-de-auditoría)
9. [Notificaciones](#9-notificaciones)
10. [Preguntas Frecuentes](#10-preguntas-frecuentes)
11. [Soporte Técnico](#11-soporte-técnico)
12. [Glosario de Términos](#12-glosario-de-términos)
13. [Anexos](#13-anexos)

---

## 1. Introducción

### 1.1 ¿Qué es SATC?

El **Sistema de Administración de Trámites de Corpochivor (SATC)** es una plataforma para gestionar los procesos administrativos de la entidad: proceso sancionatorio, infracciones, gestión documental y registro de involucrados.

### 1.2 Módulos del Sistema

| Módulo                         | Descripción                                              |
| ------------------------------ | -------------------------------------------------------- |
| **Expedientes Sancionatorios** | Gestión del proceso sancionatorio completo               |
| **Infracciones**               | Gestión de expedientes de infracción e informes técnicos |
| **Gestión Documental**         | Creación, revisión y aprobación de documentos            |
| **Involucrados**               | Registro único de personas vinculadas a procesos         |
| **Administración**             | Gestión de usuarios y roles                              |
| **Auditoría**                  | Historial de acciones sobre todos los módulos            |

El menú lateral muestra únicamente las secciones a las que tienes acceso según tu rol. Si necesitas acceso a un módulo adicional, contacta al administrador del sistema.

---

## 2. Acceso al Sistema

### 2.1 Requisitos Técnicos

**Navegadores compatibles:**
- Google Chrome 120+
- Microsoft Edge 120+
- Firefox 120+
- Safari 17+

**Conectividad:** Red local de la entidad.

### 2.2 Inicio de Sesión

1. Accede a la URL del sistema en la red de la entidad
2. Ingresa tu **correo electrónico** institucional y tu **contraseña**
3. Click en **"Iniciar Sesión"**

El sistema muestra únicamente las secciones correspondientes a tu rol.

> Si inicias sesión desde un segundo dispositivo, la sesión anterior se cierra automáticamente.

### 2.3 Recuperación de Contraseña

1. Click en **"¿Olvidaste tu contraseña?"** en la pantalla de login
2. Ingresa tu correo institucional
3. Recibirás un código de recuperación por email
4. Ingresa el código y establece una nueva contraseña

### 2.4 Gestión de tu Cuenta

Desde el menú superior derecho → **"Mi Perfil"** puedes:

- Ver tus datos: nombre, documento, correo y rol asignado
- Actualizar tu **correo electrónico**
- Cambiar tu **contraseña** (requiere ingresar la contraseña actual)

No puedes cambiar tu propio rol desde esta pantalla.

---

## 3. Módulo de Expedientes Sancionatorios

### 3.1 Etapas del Proceso Sancionatorio

El sistema gestiona las siguientes etapas procesales:

1. Indagación preliminar
2. Medida preventiva
3. Inicio del proceso sancionatorio
4. Formulación de cargos
5. Apertura / cierre de etapa probatoria
6. Decisión de fondo
7. Ejecución de la sanción
8. Cesación

### 3.2 Crear un Expediente

1. Menú lateral → **"Expedientes"** → **"Gestionar"**
2. Click en **"Nuevo Expediente"**
3. Completa el formulario con los datos del caso
4. Guarda

El sistema asigna automáticamente un número de radicado al expediente.

### 3.3 Ver el Detalle de un Expediente

Desde la lista de expedientes, click sobre el expediente. Verás:

- Datos generales del caso
- Quejoso y recursos afectados
- Involucrados vinculados
- Etapas procesales registradas
- Actos administrativos
- Comunicaciones y notificaciones

### 3.4 Registrar Etapas y Actos Administrativos

Solo puedes editar y registrar etapas en expedientes donde eres el **encargado asignado**. Puedes consultar (solo lectura) expedientes de otros abogados pero no modificarlos.

Para registrar una etapa:

1. Abre el expediente
2. Selecciona la etapa correspondiente
3. Completa los datos requeridos
4. Guarda

### 3.5 Descargar PDF del Expediente

Desde el detalle del expediente → click en **"Descargar PDF"**.

### 3.6 Consultar Expedientes (solo lectura)

Menú lateral → **"Expedientes"** → **"Consultar"**

Permite buscar y ver cualquier expediente sin posibilidad de modificar. Filtros disponibles: radicado, fecha, estado, encargado. También permite descargar el PDF.

### 3.7 Alertas de Términos

Menú lateral → **"Expedientes"** → **"Alertas"**

Panel de solo lectura con expedientes próximos a vencer o con términos ya vencidos, con indicadores visuales de urgencia.

### 3.8 Asignar Encargados

Menú lateral → **"Expedientes"** → **"Asignar"**

- **Individual:** Cambia el encargado de un expediente específico
- **Masiva:** Selecciona varios expedientes y asigna el mismo encargado con una sola acción

Desde esta vista no tienes acceso al contenido interno de los expedientes.

---

## 4. Módulo de Infracciones

### 4.1 Etapas del Proceso de Infracción

1. Respuesta al emplazamiento
2. Medida preventiva
3. Acto de cierre

### 4.2 Crear un Expediente de Infracción

1. Menú lateral → **"Infracciones"** → **"Gestionar"**
2. Click en **"Nuevo Expediente de Infracción"**
3. Completa el formulario
4. Guarda

Solo puedes editar el expediente si eres el **encargado asignado**.

Desde el detalle del expediente puedes ver los involucrados asociados, subir documentos relacionados y descargar el PDF unificado.

### 4.3 Informes Técnicos — Coordinador

Menú lateral → **"Infracciones"** → **"Asignar Informes"**

1. Ve la lista de expedientes que requieren informe técnico
2. Selecciona el profesional que elaborará el informe
3. Asigna el informe (VISITA, CONCEPTO TÉCNICO, etc.)
4. Puedes reasignar o cancelar una asignación existente
5. Sigue el estado de cada informe: pendiente, en proceso, entregado
6. Confirma la recepción del informe una vez entregado

### 4.4 Informes Técnicos — Profesional técnico

Los profesionales que tienen asignado el permiso `subir_informes` **no tienen pestaña propia en el menú**. Acceden a sus asignaciones desde la vista del expediente de infracción o mediante la notificación recibida.

1. Recibe notificación de nueva asignación
2. Accede al expediente de infracción correspondiente
3. Sube el archivo del informe técnico completado

### 4.5 Consultar Infracciones (solo lectura)

Menú lateral → **"Infracciones"** → **"Consultar"**

Permite ver el detalle completo de cualquier expediente de infracción y consultar los informes técnicos asociados. Permite descargar el PDF. No hay acceso a formularios de edición.

### 4.6 Alertas de Infracciones

Menú lateral → **"Infracciones"** → **"Alertas"**

Panel de alertas de vencimiento de términos con indicadores de urgencia por fecha límite.

### 4.7 Asignar Encargados en Infracciones

Menú lateral → **"Infracciones"** → **"Asignar"**

- **Individual:** Cambia el encargado de un expediente
- **Masiva:** Selecciona varios expedientes y asigna el mismo encargado

---

## 5. Módulo de Gestión de Documentos

### 5.1 Flujo de Aprobación

```
Creador sube documento
        │
        └─► Estado: En Revisión
                │
        Revisor analiza
                ├─ Aprueba ──► (siguiente revisor, o Estado: Aprobado si es el último)
                │
                └─ Devuelve con comentarios ──► Estado: Devuelto
                                                      │
                                               Creador recibe comentarios
                                               Sube nueva versión
                                                      │
                                               Vuelve a: En Revisión
```

El documento queda **Aprobado** cuando todos los revisores asignados han aprobado.

### 5.2 Crear un Documento

1. Menú lateral → **"Documentos"**
2. Click en **"Crear Nuevo"**
3. Completa el formulario:
   - Nombre del documento
   - Descripción
   - Archivo adjunto
   - Selección de revisores (uno o más)
4. Click en **"Crear Documento"**

El sistema escanea el archivo con antivirus antes de guardarlo y detecta archivos duplicados automáticamente. Una vez creado, notifica a cada revisor asignado.

**Formatos permitidos:** `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.txt`, `.jpg`, `.jpeg`, `.png`, `.gif`, `.zip`, `.rar`  
**Tamaño máximo:** 10 MB por archivo.

### 5.3 Subir una Nueva Versión

Cuando un revisor devuelve el documento:

1. Recibes notificación con los comentarios del revisor
2. Accede al documento desde tu lista
3. Click en **"Subir Nueva Versión"**
4. Selecciona el archivo corregido
5. El documento vuelve automáticamente a estado **En Revisión** y notifica a los revisores

### 5.4 Revisar un Documento

1. Recibes notificación de documento asignado para revisión
2. Menú lateral → **"Documentos"**
3. Descarga el archivo para revisarlo
4. Elige:

**Aprobar:** Click en **"Aprobar"** — el documento avanza al siguiente revisor o pasa a **Aprobado** si eres el último.

**Devolver:** Click en **"Devolver"** — ingresa tus observaciones (obligatorio) — el documento regresa al creador.

Puedes ver el historial de versiones y revisiones anteriores del documento.

### 5.5 Estados del Documento

| Estado          | Significado                                              |
| --------------- | -------------------------------------------------------- |
| **En Revisión** | Esperando aprobación de uno o más revisores              |
| **Aprobado**    | Todos los revisores asignados han aprobado               |
| **Devuelto**    | Al menos un revisor lo devolvió; requiere corrección     |

---

## 6. Módulo de Involucrados

Menú lateral → **"Involucrados"** → **"Gestionar"**

Mantiene un **registro único** de personas naturales o jurídicas vinculadas a procesos, evitando duplicar información entre expedientes.

**Funcionalidades:**

- **Buscar:** por tipo de documento (CC, CE, NIT) y número
- **Crear:** registrar una nueva persona si no existe en el sistema
- **Editar:** actualizar datos de contacto de una persona ya registrada
- **Historial:** ver en qué expedientes aparece una persona registrada

---

## 7. Módulo de Administración

### 7.1 Crear un Usuario

Menú lateral → **"Administración"** → **"Agregar usuario"**

1. Completa el formulario:
   - Número de documento
   - Nombre completo
   - Correo electrónico
   - Contraseña inicial
   - Rol asignado
2. Click en **"Crear Usuario"**

El usuario queda activo de inmediato.

### 7.2 Gestionar Usuarios Existentes

Menú lateral → **"Administración"** → **"Gestionar usuarios"**

- **Buscar** por nombre, documento o correo
- **Editar** nombre, correo y rol
- **Activar o desactivar** (bloquear acceso sin eliminar al usuario)

No existe opción de borrado permanente de usuarios. Al desactivar un usuario, sus sesiones activas quedan invalidadas y su historial se conserva.

### 7.3 Gestionar Roles y Permisos

Menú lateral → **"Administración"** → **"Roles"**

- Ver la lista de roles con los permisos asignados a cada uno
- Crear un rol nuevo
- Editar roles existentes: cambiar nombre y asignar o quitar permisos
- Eliminar roles (solo si no tienen usuarios asignados)

Los cambios en los permisos de un rol se reflejan de inmediato sin que los usuarios necesiten cerrar sesión.

> Para el detalle completo de qué desbloquea cada permiso, ver `MANUAL_PERMISOS_SATC.md`.

---

## 8. Módulo de Auditoría

Menú lateral → **"Auditoría"**

Todos los registros de auditoría son de **solo lectura** y generados automáticamente. Cada área tiene su propia subsección:

| Subsección        | Qué muestra                                                  |
| ----------------- | ------------------------------------------------------------ |
| **Usuarios**      | Logins, cambios de contraseña, creación/edición de usuarios  |
| **Expedientes**   | Creación, edición, cambios de encargado, registro de etapas  |
| **Involucrados**  | Creación y modificaciones de registros de personas           |
| **Infracciones**  | Creación, edición, asignaciones, subida de informes          |

En todas las subsecciones puedes filtrar por usuario, tipo de acción y rango de fechas. Cada entrada muestra los **datos anteriores y los datos nuevos** de la modificación.

---

## 9. Notificaciones

El sistema envía notificaciones automáticas según tu rol:

| Evento                                      | Quién recibe la notificación          |
| ------------------------------------------- | ------------------------------------- |
| Documento asignado para revisión            | Revisor asignado                      |
| Documento aprobado                          | Creador del documento                 |
| Documento devuelto con comentarios          | Creador del documento                 |
| Informe técnico asignado                    | Profesional técnico asignado          |

Las notificaciones se visualizan en el **ícono de campana** en la barra superior del sistema.

---

## 10. Preguntas Frecuentes

**P: ¿Qué hago si olvidé mi contraseña?**

R: Usa **"¿Olvidaste tu contraseña?"** en la pantalla de login. Recibirás un código en tu correo institucional.

**P: Mi sesión se cerró sola al entrar desde otro equipo. ¿Es normal?**

R: Sí. El sistema solo permite una sesión activa por usuario. Una nueva sesión invalida la anterior automáticamente.

**P: No aparece una sección del menú que necesito usar.**

R: Tu rol no tiene ese permiso habilitado. Contacta al administrador del sistema para que ajuste los permisos de tu rol.

**P: ¿Cómo sé qué expedientes son míos?**

R: En **"Expedientes" → "Gestionar"** aparecen todos los expedientes. Solo puedes editar aquellos donde figuras como encargado asignado.

**P: ¿Puedo cambiar los revisores de un documento después de crearlo?**

R: No. Los revisores se asignan al crear el documento y no se pueden modificar después.

**P: ¿Los revisores deben aprobar en un orden específico?**

R: No. El documento queda aprobado cuando todos los revisores asignados han aprobado, sin importar el orden.

**P: El sistema rechazó mi archivo al subirlo. ¿Por qué?**

R: Los motivos posibles son: formato no permitido, archivo mayor a 10 MB, o detección de virus por el antivirus del sistema.

**P: ¿Se guarda un historial de los cambios que hago?**

R: Sí. Cada acción queda registrada en el módulo de Auditoría con usuario, fecha, hora, IP y los datos antes y después del cambio.

---

## 11. Soporte Técnico

Al contactar soporte, proporciona:

1. Usuario y descripción de tu rol
2. Navegador y versión
3. Descripción detallada del problema
4. Pasos para reproducir el error
5. Captura de pantalla (si es posible)
6. Fecha y hora del incidente
7. Mensaje de error exacto (si aparece)

**Problemas comunes:**

- **No puedo acceder al sistema:** verifica que estés en la red de la entidad, que el navegador sea compatible y que tu usuario esté activo.
- **Error al subir archivo:** verifica tamaño (máx. 10 MB) y que el formato esté entre los permitidos.
- **No veo una sección del menú:** contacta al administrador para revisar los permisos de tu rol.

---

## 12. Glosario de Términos

| Término                 | Definición                                                                        |
| ----------------------- | --------------------------------------------------------------------------------- |
| **Acto Administrativo** | Documento oficial que formaliza decisiones en el proceso sancionatorio            |
| **Cesación**            | Etapa del proceso sancionatorio que da por terminado el procedimiento             |
| **Encargado**           | Usuario responsable de gestionar un expediente específico                         |
| **Expediente**          | Conjunto de datos, etapas y documentos de un caso administrativo                 |
| **Informe técnico**     | Documento elaborado por un profesional técnico dentro de un proceso de infracción |
| **Involucrado**         | Persona natural o jurídica vinculada a un proceso administrativo                  |
| **Radicado**            | Número único que identifica un expediente                                         |
| **Rol**                 | Conjunto de permisos asignado a un usuario                                        |

---

## 13. Anexos

### Anexo A: Códigos de Error Comunes

| Código  | Mensaje                | Solución                          |
| ------- | ---------------------- | --------------------------------- |
| **401** | No autorizado          | Vuelve a iniciar sesión           |
| **403** | Sin permisos           | Contacta al administrador         |
| **404** | No encontrado          | Verifica el radicado o ID         |
| **429** | Demasiadas solicitudes | Espera unos minutos y reintenta   |
| **500** | Error del servidor     | Reporta a soporte técnico         |

### Anexo B: Normativa Aplicable

- Ley 1437 de 2011 — Código de Procedimiento Administrativo y de lo Contencioso Administrativo
- Ley 1581 de 2012 — Protección de Datos Personales

---

**Documento Confidencial - Uso Interno Gubernamental**

**© 2026 - Corpochivor - Todos los derechos reservados**
