# HISTORIAS DE USUARIO — SISTEMA SATC
**Sistema de Administración de Trámites de Corpochivor**
**Versión:** 1.0 
**Fecha:** 1 de julio de 2026


## 1. Módulo: Todo usuario (general)

### HU-GEN-01 — Inicio de sesión
**Como** usuario registrado del sistema, **quiero** iniciar sesión con mi documento y contraseña, **para** acceder a las funcionalidades que me corresponden según mi rol.

**Criterios de aceptación:**
- Puedo iniciar sesión con documento y contraseña.
- Si las credenciales son incorrectas, recibo un mensaje de error sin detalle que revele si el usuario existe o no.
- Al iniciar sesión, el sistema me muestra únicamente el menú y las pestañas correspondientes a los permisos de mi rol.
- Si inicio sesión desde un segundo dispositivo, mi sesión anterior queda invalidada automáticamente (sesión única).
- Si mi sesión es cerrada de forma remota o expira, soy redirigido al login con un aviso, sin quedar en una pantalla inconsistente.

### HU-GEN-02 — Modificación de datos propios
**Como** usuario registrado del sistema, **quiero** consultar y actualizar mis propios datos de cuenta, **para** mantener mi información de contacto correcta y cambiar mi contraseña cuando lo necesite.

**Criterios de aceptación:**
- Puedo ver mis propios datos: nombre, documento, correo y rol asignado.
- Puedo actualizar mi correo electrónico y mi contraseña.
- Para cambiar mi contraseña, el sistema me exige la contraseña actual como verificación.
- No puedo cambiar mi propio rol ni mis propios permisos desde esta pantalla.
- Los cambios quedan registrados en el log de auditoría de usuarios.

## 2. Módulo: Administración (usuarios y roles)

### HU-ADM-01 — Gestión de roles y permisos
**Permiso:** `admin_roles_y_permisos`
**Como** administrador del sistema, **quiero** crear, editar y eliminar roles y asignarles permisos específicos, **para** controlar de forma centralizada qué puede hacer cada perfil de usuario en la plataforma.

**Criterios de aceptación:**
- Puedo ver la lista completa de roles existentes, con los permisos asignados a cada uno.
- Puedo crear un rol nuevo con un nombre personalizado.
- Puedo asignar o quitar permisos individuales a un rol existente.
- No puedo eliminar un rol que todavía tiene usuarios asignados.
- Los cambios de permisos en un rol se reflejan de inmediato en todos los usuarios que lo tienen asignado (sin necesidad de cerrar sesión).

### HU-ADM-02 — Creación de usuarios
**Permiso:** `admin_registrar_usuarios`
**Como** administrador, **quiero** registrar nuevos usuarios en el sistema con su rol asignado, **para** darles acceso a la plataforma según su función institucional.

**Criterios de aceptación:**
- Puedo completar un formulario con documento, nombre completo, correo, contraseña inicial y rol.
- Solo puedo asignar roles que ya existen previamente.
- El usuario queda activo de forma inmediata tras el registro.

### HU-ADM-03 — Gestión de usuarios existentes
**Permiso:** `admin_gestionar_usuarios`
**Como** administrador, **quiero** consultar, editar, activar o desactivar usuarios existentes, **para** mantener actualizada la base de usuarios sin perder el historial de cada cuenta.

**Criterios de aceptación:**
- Puedo buscar un usuario por nombre, documento o correo.
- Puedo editar nombre, correo y rol de un usuario.
- Puedo desactivar un usuario para bloquear su acceso sin eliminarlo.
- No existe opción de borrado permanente de usuarios desde esta pantalla.

---

## 3. Módulo: Expedientes (proceso sancionatorio)

### HU-EXP-01 — Gestión completa de expedientes
**Permiso:** `expediente_gestionar`
**Como** abogado encargado de un expediente, **quiero** crear expedientes y registrar sus etapas procesales, **para** llevar la trazabilidad completa del proceso sancionatorio de principio a fin.

**Criterios de aceptación:**
- Puedo crear un expediente nuevo con radicado, fecha y datos del caso.
- Puedo ver el detalle completo: quejoso, recursos afectados, involucrados, etapas, actos administrativos y comunicaciones.
- Solo puedo editar o registrar etapas en expedientes donde figuro como encargado asignado.
- Puedo descargar el PDF unificado del expediente.
- Puedo consultar (solo lectura) expedientes de otros abogados, pero no modificarlos.

### HU-EXP-02 — Consulta de expedientes (solo lectura)
**Permiso:** `expediente_consultar`
**Como** consultor, **quiero** ver el detalle completo de cualquier expediente sin poder modificarlo, **para** hacer seguimiento o análisis sin riesgo de alterar la información del proceso.

**Criterios de aceptación:**
- Puedo filtrar expedientes por radicado, fecha, estado o encargado.
- Puedo ver todas las etapas, actos y documentos adjuntos de cualquier expediente.
- No tengo acceso a ningún formulario de creación o edición.
- Puedo descargar el PDF del expediente.

### HU-EXP-03 — Alertas de vencimiento de términos
**Permiso:** `expediente_alertas`
**Como** abogado o coordinador, **quiero** ver un panel de alertas sobre expedientes próximos a vencer o ya vencidos, **para** priorizar mi trabajo y evitar el incumplimiento de términos procesales.

**Criterios de aceptación:**
- El panel muestra expedientes próximos a vencer y expedientes con términos ya vencidos.
- Cada expediente tiene un indicador visual de urgencia según su criticidad.
- El panel es de solo lectura — no permite tomar acciones desde ahí.

### HU-EXP-04 — Asignación de encargados
**Permiso:** `expediente_asignar`
**Como** coordinador de expedientes, **quiero** asignar o reasignar el abogado encargado de uno o varios expedientes, **para** distribuir la carga de trabajo del equipo jurídico.

**Criterios de aceptación:**
- Puedo cambiar el encargado de un expediente individual.
- Puedo seleccionar varios expedientes y asignarles un mismo encargado nuevo (asignación masiva).
- Solo puedo asignar como encargados a usuarios que tienen el permiso `expediente_gestionar`.
- No tengo acceso al contenido interno de los expedientes desde esta vista.

---

## 4. Módulo: Infracciones

### HU-INF-01 — Gestión completa de infracciones
**Permiso:** `infraccion_gestionar`
**Como** abogado encargado de infracciones, **quiero** crear expedientes de infracción y registrar sus etapas, **para** documentar el proceso de emplazamiento, medida preventiva y cierre.

**Criterios de aceptación:**
- Puedo crear un expediente de infracción nuevo.
- Puedo registrar y editar las etapas: respuesta al emplazamiento, medida preventiva y acto de cierre.
- Puedo subir documentos y archivos relacionados al expediente.
- Solo puedo editar expedientes donde soy el encargado asignado.
- Puedo descargar el PDF unificado del expediente.

### HU-INF-02 — Consulta de infracciones (solo lectura)
**Permiso:** `infraccion_consultar`
**Como** consultor, **quiero** ver el detalle de cualquier expediente de infracción y sus informes técnicos, **para** hacer seguimiento sin poder alterar la información.

**Criterios de aceptación:**
- Puedo ver el detalle completo de cualquier expediente de infracción.
- Puedo consultar los informes técnicos asociados (visita, concepto, etc.).
- Puedo descargar el PDF sin necesidad de ser el encargado.
- No tengo acceso a formularios de edición.

### HU-INF-03 — Alertas de infracciones
**Permiso:** `infraccion_alertas`
**Como** abogado o coordinador de infracciones, **quiero** ver un panel de alertas de vencimiento de términos, **para** anticiparme a los plazos del proceso.

**Criterios de aceptación:**
- El panel muestra expedientes de infracción con fechas límite próximas o vencidas.
- Cada expediente tiene un indicador de urgencia.

### HU-INF-04 — Asignación de encargados en infracciones
**Permiso:** `infraccion_asignar`
**Como** coordinador de infracciones, **quiero** asignar o reasignar el encargado de uno o varios expedientes de infracción, **para** distribuir la carga de trabajo del equipo.

**Criterios de aceptación:**
- Puedo cambiar el encargado de un expediente individual o de varios a la vez (bulk).
- Solo puedo elegir encargados entre usuarios con el permiso `infraccion_gestionar`.

### HU-INF-05 — Asignación de informes técnicos
**Permiso:** `infraccion_asignar_informes`
**Como** coordinador de infracciones, **quiero** asignar la elaboración de un informe técnico a un profesional específico, **para** que el proceso de visita o concepto técnico quede formalmente encargado a alguien.

**Criterios de aceptación:**
- Puedo ver la lista de expedientes que requieren informe técnico.
- Puedo ver los profesionales disponibles (usuarios con `subir_informes`) para asignar.
- Puedo reasignar o cancelar una asignación existente.
- Puedo ver el estado de cada informe (pendiente, en proceso, entregado) y confirmar su recepción.

### HU-INF-06 — Elaboración y entrega de informes técnicos
**Permiso:** `subir_informes`
**Como** profesional técnico, **quiero** recibir asignaciones de informes técnicos y subir el archivo una vez completado, **para** cumplir con la parte técnica del proceso de infracción que me corresponde.

**Criterios de aceptación:**
- Recibo notificación cuando se me asigna un nuevo informe técnico.
- Puedo ver mis informes pendientes de entrega.
- Puedo subir el archivo del informe completado.
- No tengo ninguna pestaña de menú visible — accedo a mis asignaciones dentro de la vista de infracción.

---

## 5. Módulo: Documentos

### HU-DOC-01 — Acceso al módulo de documentos
**Permiso:** `documento_gestionar`
**Como** funcionario del módulo de documentos, **quiero** acceder a la sección de documentos, **para** poder crear o revisar documentos según mi rol específico.

**Criterios de aceptación:**
- Veo la categoría "Documentos" en el menú lateral.
- Si no tengo además `documento_crear` o `documento_revisar`, recibo un aviso de permisos insuficientes al intentar listar documentos.

### HU-DOC-02 — Creación y carga de documentos
**Permiso:** `documento_crear`
**Como** creador de documentos, **quiero** subir un documento nuevo y enviarlo a revisión, **para** que quede formalmente registrado y aprobado dentro del sistema.

**Criterios de aceptación:**
- Puedo completar un formulario con nombre, descripción y archivo adjunto.
- El archivo pasa por verificación antivirus antes de aceptarse.
- Puedo elegir uno o varios revisores de la lista de usuarios con `documento_revisar`.
- Recibo notificación cuando el documento es aprobado o devuelto.
- Si es devuelto, puedo subir una nueva versión, que vuelve a quedar en estado "en revisión".

### HU-DOC-03 — Revisión y aprobación de documentos
**Permiso:** `documento_revisar`
**Como** revisor de documentos, **quiero** ver los documentos asignados para mi revisión y aprobarlos o devolverlos con comentarios, **para** garantizar la calidad de la documentación antes de su aprobación final.

**Criterios de aceptación:**
- Recibo notificación cuando se me asigna un documento para revisar.
- Puedo descargar el archivo para revisarlo.
- Puedo aprobar el documento o devolverlo con comentarios.
- Puedo ver el historial de versiones y revisiones anteriores del documento.

---

## 6. Módulo: Involucrados

### HU-INV-01 — Gestión de personas involucradas
**Permiso:** `involucrado_gestionar`
**Como** gestor de involucrados, **quiero** registrar y consultar personas involucradas en procesos administrativos, **para** mantener un registro único y evitar duplicar información de una misma persona entre expedientes.

**Criterios de aceptación:**
- Puedo buscar una persona por tipo y número de documento (CC, CE, NIT).
- Puedo crear un nuevo registro de persona si no existe previamente.
- Puedo editar los datos de contacto de una persona ya registrada.
- Puedo ver el historial de en qué expedientes aparece una persona.

---

## 7. Módulo: Auditoría

Todos los permisos de este módulo son de **solo lectura**.

### HU-AUD-01 — Auditoría de usuarios
**Permiso:** `auditoria_usuarios`
**Como** jefe de área, **quiero** consultar el registro de todas las acciones de administración de usuarios, **para** verificar quién hizo cada cambio y detectar accesos indebidos.

**Criterios de aceptación:**
- Puedo ver logins, cambios de contraseña, creación/edición de usuarios y cambios de rol.
- Puedo filtrar por usuario, tipo de evento y rango de fechas.
- Puedo ver la IP de origen de cada acción registrada.

### HU-AUD-02 — Auditoría de expedientes sancionatorios
**Permiso:** `auditoria_expedientes`
**Como** jefe de área, **quiero** consultar el historial completo de cambios sobre expedientes sancionatorios, **para** verificar la trazabilidad del proceso ante cualquier duda o reclamo.

**Criterios de aceptación:**
- Puedo filtrar por radicado, usuario, tipo de acción y fechas.
- Puedo ver los datos anteriores y nuevos de cada modificación registrada.

### HU-AUD-03 — Auditoría de involucrados
**Permiso:** `auditoria_involucrados`
**Como** jefe de área, **quiero** ver el registro de creación y modificación de personas involucradas, **para** confirmar que la información de contacto se mantiene correctamente actualizada y trazable.

**Criterios de aceptación:**
- Puedo ver el historial completo de cambios sobre cualquier registro de persona involucrada.

### HU-AUD-04 — Auditoría de infracciones
**Permiso:** `auditoria_infracciones`
**Como** jefe de área, **quiero** consultar el historial completo de acciones sobre expedientes de infracción, **para** verificar la trazabilidad de creación, asignaciones y subida de informes.

**Criterios de aceptación:**
- Puedo ver creación, edición, asignaciones y cambios de encargado de cualquier expediente de infracción.
- Puedo ver los datos antes y después de cada modificación.

---

