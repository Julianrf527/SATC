# HISTORIAS DE USUARIO — SISTEMA SATC
**Sistema de Administración de Trámites de Corpochivor**
**Versión:** 1.1 
**Fecha:** 19 de octubre de 2026

> **Cambios en la versión 1.1:** se actualizan los nombres de los permisos al catálogo vigente (32 permisos, ver `MANUAL_PERMISOS_SATC.md` v1.2) y los criterios de las HU existentes que cambiaron en octubre de 2026; se agregan las HU de administración de permisos (HU-ADM-04 y HU-ADM-05), de alertas (HU-ALE-01 y HU-ALE-02) y del módulo Concesiones de Aguas Superficiales (HU-CON-01 a HU-CON-18).


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
- Solo puedo otorgar a un rol los permisos que mi propio rol tiene, y solo veo los roles cuyos permisos tengo.
- Los cambios de permisos en un rol se aplican a todos los usuarios que lo tienen asignado sin cerrar sesión; los servicios pueden tardar hasta 5 minutos en reflejarlos y el menú lateral se actualiza al recargar la página.

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

### HU-ADM-04 — Descripción obligatoria de cada permiso
**Permiso:** `admin_roles_y_permisos`
**Como** administrador del sistema, **quiero** que cada permiso tenga una descripción corta de lo que desbloquea y para qué sirve, **para** asignar permisos a los roles sabiendo exactamente qué otorgo.

**Criterios de aceptación:**
- En la pantalla de roles cada permiso muestra su descripción con el formato "Desbloquea X. Sirve para Y.".
- Al crear o editar un permiso, la descripción es obligatoria y admite máximo 200 caracteres (la pantalla muestra el contador); el servidor rechaza una descripción vacía o más larga.
- Los permisos del catálogo oficial traen su descripción desde la instalación; lo que edite desde la pantalla no se sobrescribe al reiniciar el sistema.

### HU-ADM-05 — Dependencias obligatorias entre permisos
**Permiso:** `admin_roles_y_permisos`
**Como** administrador del sistema, **quiero** que la pantalla de roles me impida armar un rol con un permiso al que le falta otro que necesita, **para** no crear roles que abren una pantalla sin poder usarla.

**Criterios de aceptación:**
- Un permiso que depende de otro aparece bloqueado (no se puede marcar) mientras el requerido no esté marcado, y debajo se indica "Requiere: …".
- Al desmarcar un permiso requerido se desmarcan en cascada los que dependen de él, y la pantalla me avisa cuáles se quitaron.
- El botón "Todos" de una categoría marca primero los requeridos y luego sus dependientes.
- Si un rol existente tiene un permiso sin su requerido, la pantalla lo lista y no deja guardar hasta corregirlo.
- El servidor repite la validación: si se intenta guardar un rol que incumple, lo rechaza e indica qué falta (por ejemplo, «infraccion_alertas» requiere «infraccion_consultar»).
- Los roles que ya existían e incumplen siguen funcionando hasta que se vuelvan a guardar; soporte técnico puede listarlos con un reporte de solo lectura.
- Las 17 dependencias vigentes son las de la sección 4 de `MANUAL_PERMISOS_SATC.md`.

---

## 3. Módulo: Sancionatorio (expedientes sancionatorios)

### HU-EXP-01 — Gestión completa de expedientes
**Permiso:** `sancionatorio_gestionar`
**Como** abogado encargado de un expediente, **quiero** crear expedientes y registrar sus etapas procesales, **para** llevar la trazabilidad completa del proceso sancionatorio de principio a fin.

**Criterios de aceptación:**
- Puedo crear un expediente nuevo con radicado, fecha y datos del caso.
- Puedo ver el detalle completo: quejoso, recursos afectados, involucrados, etapas, actos administrativos y comunicaciones.
- Solo puedo editar o registrar etapas en expedientes donde figuro como encargado asignado.
- Puedo descargar el PDF unificado del expediente.
- Para ver (en solo lectura) expedientes de otros abogados necesito además `sancionatorio_consultar`; sin él, el sistema responde "sin permisos" sin revelar si el expediente existe.

### HU-EXP-02 — Consulta de expedientes (solo lectura)
**Permiso:** `sancionatorio_consultar`
**Como** consultor, **quiero** ver el detalle completo de cualquier expediente sin poder modificarlo, **para** hacer seguimiento o análisis sin riesgo de alterar la información del proceso.

**Criterios de aceptación:**
- Puedo filtrar expedientes por radicado, fecha, estado o encargado.
- Puedo ver todas las etapas, actos y documentos adjuntos de cualquier expediente.
- No tengo acceso a ningún formulario de creación o edición.
- Puedo descargar el PDF del expediente.

### HU-EXP-03 — Alertas de vencimiento de términos
**Permiso:** `sancionatorio_alertas` (exige `sancionatorio_consultar`)
**Como** abogado o coordinador, **quiero** ver un panel de alertas sobre expedientes próximos a vencer o ya vencidos, **para** priorizar mi trabajo y evitar el incumplimiento de términos procesales.

**Criterios de aceptación:**
- El panel muestra expedientes próximos a vencer y expedientes con términos ya vencidos.
- Cada expediente tiene un indicador visual de urgencia según su criticidad.
- El panel es de solo lectura: no permite modificar el expediente, pero cada alerta enlaza a Gestionar o a Consultar (ver HU-ALE-02).
- Puedo filtrar entre "Mis expedientes" y "Todos" (ver HU-ALE-02).

### HU-EXP-04 — Asignación de encargados
**Permiso:** `sancionatorio_asignar` (exige `sancionatorio_consultar`)
**Como** coordinador de expedientes, **quiero** asignar o reasignar el abogado encargado de uno o varios expedientes, **para** distribuir la carga de trabajo del equipo jurídico.

**Criterios de aceptación:**
- Puedo cambiar el encargado de un expediente individual.
- Puedo seleccionar varios expedientes y asignarles un mismo encargado nuevo (asignación masiva).
- Solo puedo asignar como encargados a usuarios que tienen el permiso `sancionatorio_gestionar`; si se envía otro usuario, el servidor rechaza la asignación.
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
- Para ver expedientes de otros encargados necesito además `infraccion_consultar`; sin él, el sistema responde "sin permisos" sin revelar si el expediente existe.
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
**Permiso:** `infraccion_alertas` (exige `infraccion_consultar`)
**Como** abogado o coordinador de infracciones, **quiero** ver un panel de alertas de vencimiento de términos, **para** anticiparme a los plazos del proceso.

**Criterios de aceptación:**
- El panel muestra expedientes de infracción con fechas límite próximas o vencidas.
- Cada expediente tiene un indicador de urgencia.
- Puedo filtrar entre "Mis expedientes" y "Todos", y cada alerta enlaza a Gestionar o a Consultar (ver HU-ALE-02).

### HU-INF-04 — Asignación de encargados en infracciones
**Permiso:** `infraccion_asignar` (exige `infraccion_consultar`)
**Como** coordinador de infracciones, **quiero** asignar o reasignar el encargado de uno o varios expedientes de infracción, **para** distribuir la carga de trabajo del equipo.

**Criterios de aceptación:**
- Puedo cambiar el encargado de un expediente individual o de varios a la vez (bulk).
- Solo puedo elegir encargados entre usuarios con el permiso `infraccion_gestionar`; si se envía otro usuario, el servidor rechaza la asignación.

### HU-INF-05 — Asignación de informes técnicos
**Permiso:** `infraccion_asignar_informes` (exige `infraccion_consultar`)
**Como** coordinador de infracciones, **quiero** asignar la elaboración de un informe técnico a un profesional específico, **para** que el proceso de visita o concepto técnico quede formalmente encargado a alguien.

**Criterios de aceptación:**
- Puedo ver la lista de expedientes que requieren informe técnico.
- Puedo ver los profesionales disponibles (usuarios con `infraccion_informes_subir`) y los revisores disponibles (usuarios con `infraccion_informes_revisar`) para asignar.
- Si elijo un usuario que no tiene el permiso correspondiente, el servidor rechaza la asignación.
- Puedo reasignar o cancelar una asignación existente.
- Puedo ver el estado de cada informe (pendiente, en proceso, entregado) y confirmar su recepción.

### HU-INF-06 — Elaboración y entrega de informes técnicos
**Permiso:** `infraccion_informes_subir` (exige `infraccion_consultar`)
**Como** profesional técnico, **quiero** recibir asignaciones de informes técnicos y subir el archivo una vez completado, **para** cumplir con la parte técnica del proceso de infracción que me corresponde.

**Criterios de aceptación:**
- Recibo notificación cuando se me asigna un nuevo informe técnico.
- Puedo ver mis informes pendientes de entrega.
- Puedo subir el archivo del informe completado.
- Accedo a mis asignaciones desde la entrada **Mis informes** de Infracciones (`/infraction/my-reports`).

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

## 8. Módulo: Alertas de vencimiento (Sancionatorio e Infracciones)

### HU-ALE-01 — Tarjeta de alertas en el detalle del expediente
**Permiso:** `sancionatorio_gestionar` o `sancionatorio_consultar` / `infraccion_gestionar` o `infraccion_consultar`
**Como** abogado o consultor, **quiero** ver las alertas de vencimiento dentro del detalle de un expediente, tanto en Gestionar como en Consultar, **para** conocer los términos del expediente sin tener que ir a la pestaña Alertas.

**Criterios de aceptación:**
- La tarjeta de alertas aparece en la información del expediente en la pantalla Gestionar y también en la pantalla Consultar (solo lectura).
- Muestra cada alerta con su semáforo (verde, amarillo, rojo, vencido).
- Aplica la misma regla de acceso que el resto del expediente: con el permiso de consultar veo las alertas de cualquier expediente; con solo el de gestionar, únicamente las de los expedientes a mi cargo; en otro caso el sistema responde "sin permisos" sin revelar si el expediente existe.

### HU-ALE-02 — Pestaña Alertas con filtro "Mis expedientes / Todos"
**Permiso:** `sancionatorio_alertas` / `infraccion_alertas` (cada uno exige el permiso de consultar de su módulo)
**Como** abogado, coordinador o supervisor, **quiero** filtrar la pestaña Alertas entre mis expedientes y todos los expedientes, e ir desde cada alerta al expediente, **para** priorizar mi trabajo o hacer seguimiento al de todo el equipo.

**Criterios de aceptación:**
- La pestaña abre por defecto en "Mis expedientes": vencimientos de los expedientes de los que soy responsable.
- Con "Todos" veo los vencimientos de todos los expedientes; el servidor solo entrega esa vista a quien tiene el permiso de alertas del módulo.
- En la vista "Todos" cada alerta se marca como "Mío" u "Otro responsable".
- Cada alerta enlaza a **Gestionar** si soy el responsable de ese expediente, o a **Consultar** si no lo soy.
- Puedo filtrar por radicado (coincidencia parcial), estado del semáforo y tipo de alerta; los resultados vienen paginados desde el servidor (10 por página), ordenados por urgencia y porcentaje de avance.
- El resumen por semáforo (verde, amarillo, rojo, vencido) corresponde a todo el alcance elegido, sin los demás filtros.

---

## 9. Módulo: Concesiones de Aguas Superficiales

> Reglas de negocio definidas con el área jurídica de Recurso Hídrico. Las reglas
> marcadas como provisionales están pendientes de confirmar con esa área.

### HU-CON-01 — Información base del expediente
**Permiso:** `recurso_gestionar`
**Como** abogado de Concesiones de Aguas, **quiero** registrar y editar la información base del expediente cuando llega el comprobante de pago, **para** que el trámite quede registrado desde su nacimiento con sus datos de predio, fuente y usos.

**Criterios de aceptación:**
- Registro radicado y fecha de radicado, código del expediente (p. ej. `CA 001-26`), radicado y fecha del oficio de entrada, comprobante de pago (PDF), número VITAL, nombre del predio, matrícula inmobiliaria, código catastral, municipio y vereda, tipo de fuente, nombre de la fuente, una o varias fuentes y uno o varios usos del agua.
- El radicado y el código del expediente no se pueden repetir.
- Tipos de fuente, fuentes, usos, municipios y veredas se eligen de catálogos.
- La información base se muestra organizada en cuadrícula en el detalle del expediente.
- Si otra persona modificó el expediente mientras yo lo editaba, el sistema no guarda mis cambios y me pide recargar ("Fue modificado por otra persona, recarga").

### HU-CON-02 — Solicitantes y terceros intervinientes
**Permiso:** `recurso_gestionar`
**Como** abogado de Concesiones de Aguas, **quiero** vincular y desvincular los solicitantes y los terceros intervinientes del expediente, **para** saber a quién se le comunica o notifica cada actuación.

**Criterios de aceptación:**
- Las personas se buscan o registran en el módulo de Involucrados y se vinculan al expediente; puede haber más de un solicitante.
- Si la persona es una empresa (tipo de documento NIT), es obligatorio vincular su representante legal.
- Los terceros intervinientes (personas que se oponen al permiso) se gestionan junto a los solicitantes y se pueden vincular en cualquier momento del trámite, sin exigir el auto que admite.
- Al tercero se le expide un acto que lo reconoce, que se proyecta y revisa como los demás actos (HU-CON-12).
- No puedo desvincular a un tercero que ya tiene acto, notificaciones o el acto en proyección.

### HU-CON-03 — "Asignarme para diligenciar"
**Permiso:** `recurso_gestionar`
**Como** abogado de Concesiones de Aguas, **quiero** asignarme una etapa del expediente para diligenciarla, **para** que quede claro que ese proceso está a mi cargo y nadie más lo modifique.

**Criterios de aceptación:**
- En cada etapa o acto disponible veo la opción "Asignarme para diligenciar".
- Al asignarme quedo como encargado y desde ese momento solo yo gestiono el documento de esa etapa.
- Si el proceso ya tiene encargado, nadie más puede tomarlo y no hay reasignación.
- Si dos abogados se asignan el mismo proceso al mismo tiempo, solo uno queda asignado; el otro recibe el aviso "Ya fue asignado".

### HU-CON-04 — Selección del técnico encargado
**Permiso:** `recurso_gestionar` (selecciona) / `recurso_tecnico` (es seleccionado)
**Como** abogado de Concesiones de Aguas, **quiero** elegir el técnico encargado de cada concepto técnico, **para** que el concepto quede a cargo de un profesional habilitado.

**Criterios de aceptación:**
- Solo aparecen para elegir los usuarios con el permiso `recurso_tecnico`; si se envía otro usuario, el servidor lo rechaza.
- En el auto que admite, el técnico y la fecha de visita se registran al cargar el auto firmado; en los demás conceptos (adicional, memorias, subsanación, obras) el técnico se elige cuando la etapa lo permite.
- Solo el técnico seleccionado puede cargar su concepto; lo hace desde **Mis informes**, sin entrar a Gestionar.

### HU-CON-05 — Etapa 1: Auto que admite
**Permiso:** `recurso_gestionar`
**Como** abogado encargado, **quiero** proyectar el auto que admite y cargar su versión firmada con sus documentos, **para** dar inicio formal al trámite de concesión.

**Criterios de aceptación:**
- Ninguna etapa siguiente puede existir sin el auto que admite.
- Me asigno el auto, lo proyecto y pasa por la revisión del líder jurídico y luego del líder del proyecto (HU-CON-12).
- Al cargar el auto firmado y numerado registro además el técnico y la fecha de visita técnica; con eso nace la etapa 2 (concepto técnico).
- Puedo cargar o reemplazar el oficio a la Alcaldía, la fijación del aviso y la constancia de fijación de la Alcaldía (esta última puede llegar después).
- El auto que admite solo se comunica; no se notifica (HU-CON-14).

### HU-CON-06 — Etapa 2: Concepto técnico
**Permiso:** `recurso_tecnico`
**Como** técnico seleccionado, **quiero** proyectar el concepto técnico y cargar su versión firmada con los datos de caudal, **para** que el abogado pueda continuar con la decisión del trámite.

**Criterios de aceptación:**
- El concepto existe solo si el auto que admite registró técnico y fecha de visita.
- El concepto lo revisan el líder técnico y el SIG (en cualquier orden) y después el líder del proyecto.
- Al cargar la versión firmada registro la fecha del concepto (fecha de firma), el caudal de la fuente, el caudal disponible, el caudal otorgado y el número de usuarios.
- Los campos que pide el formulario los define el servidor para cada tipo de concepto.

### HU-CON-07 — Etapa 3: Requerimiento
**Permiso:** `recurso_gestionar`
**Como** abogado encargado, **quiero** expedir un requerimiento cuando al solicitante le falta algo, y registrar su respuesta, **para** completar el trámite antes de decidir.

**Criterios de aceptación:**
- El requerimiento es opcional y solo se puede crear si existe el concepto técnico de la etapa 2.
- Se revisa por líder jurídico y luego por líder del proyecto; la versión firmada crea el acto.
- Registro la respuesta del usuario con su radicado, fecha y PDF.
- Si la respuesta debe reevaluarse, se puede pedir un concepto técnico adicional (sin visita), que revisa el líder técnico.
- El requerimiento se notifica (HU-CON-14).

### HU-CON-08 — Etapa 4: Decisión del proceso
**Permiso:** `recurso_gestionar`
**Como** abogado encargado, **quiero** proyectar la decisión y cargar su versión firmada indicando el sentido, **para** resolver la solicitud de concesión.

**Criterios de aceptación:**
- La decisión solo se puede crear si existe el auto que admite y la constancia de fijación de la Alcaldía; no requiere concepto técnico (caso de desistimiento).
- La revisan el líder jurídico y luego, en el mismo paso, el líder del proyecto y la asesora de subdirección.
- Al cargar la versión firmada indico si es OTORGADA, NEGADA o DESISTIDA; solo si es OTORGADA indico si requiere memorias de cálculo.
- La decisión se toma una sola vez por expediente.
- Puedo registrar o borrar la fecha de ejecutoria.
- La decisión se notifica a cada solicitante y a cada tercero interviniente (HU-CON-14).

### HU-CON-09 — Recurso de reposición
**Permiso:** `recurso_gestionar`
**Como** abogado, **quiero** registrar el recurso de reposición que presenta el usuario y el acto que lo resuelve, **para** dejar trazabilidad de la impugnación de la decisión.

**Criterios de aceptación:**
- El recurso solo se puede registrar si la decisión ya fue notificada.
- Primero registro el radicado, la fecha y el PDF del recurso; después un abogado se asigna el acto que lo resuelve.
- El acto que resuelve se revisa igual que la decisión (líder jurídico; luego líder del proyecto y asesora de subdirección).
- Al cargar la versión firmada indico el resultado: REPONE, CONFIRMA, MODIFICA o ADICIONA. El acto se notifica.

### HU-CON-10 — Etapa 5: Memorias de cálculo
**Permiso:** `recurso_gestionar` (abogado) / `recurso_tecnico` (técnico)
**Como** abogado o técnico, **quiero** gestionar la presentación y aprobación de las memorias de cálculo, **para** verificar los planos exigidos en la decisión.

**Criterios de aceptación:**
- La etapa solo existe si la decisión es OTORGADA y requiere memorias de cálculo.
- Registro el radicado y el PDF de los planos; el técnico seleccionado emite un concepto (sin visita) que revisa el líder técnico e indica si cumple o no cumple.
- Si no cumple, se expide un requerimiento (líder jurídico y líder del proyecto), se registra la subsanación (planos ajustados) y el técnico emite el concepto de la subsanación.
- El acto que aprueba las memorias solo se puede asignar si el último concepto dice que cumple; se revisa por líder jurídico y líder del proyecto y se notifica.

### HU-CON-11 — Etapa 6: Recibo a satisfacción de obras
**Permiso:** `recurso_gestionar` (abogado) / `recurso_tecnico` (técnico)
**Como** abogado o técnico, **quiero** gestionar el recibo a satisfacción de las obras, **para** verificar que el usuario construyó la obra o instaló el medidor o la llave.

**Criterios de aceptación:**
- La etapa solo existe si la decisión es OTORGADA y, cuando se requieren memorias, si estas ya fueron aprobadas.
- Registro el informe del usuario (radicado y PDF); el técnico seleccionado emite un concepto con visita, registra la fecha de visita e indica si cumple o no cumple; lo revisa el líder técnico.
- Si no cumple, se expide un requerimiento, se registra un nuevo informe del usuario y el técnico emite un segundo concepto con visita.
- El acto que aprueba las obras solo se puede asignar si el último concepto dice que cumple. Su cadena de revisión (líder jurídico y luego líder del proyecto) es provisional.

### HU-CON-12 — Flujo de revisión por roles y versión firmada
**Permiso:** `recurso_lider_juridico`, `recurso_lider_proyecto`, `recurso_asesora_subdireccion`, `recurso_lider_tecnico`, `recurso_sig` (revisores); abogado encargado o técnico seleccionado (sube)
**Como** revisor o encargado de un documento de Concesiones, **quiero** que cada documento pase por la cadena de revisión que le corresponde y termine en su versión firmada, **para** que solo se firme y numere lo aprobado.

**Criterios de aceptación:**
- Cada tipo de documento tiene su cadena de pasos (tabla de la sección 6 de `MANUAL_PERMISOS_SATC.md`); en cada paso deben revisar todos los permisos del paso, en cualquier orden, antes de avanzar.
- El documento les aparece en Mis informes a quienes tienen el permiso del paso pendiente, y reciben notificación.
- Al devolver, el comentario es obligatorio y puedo adjuntar un archivo; el encargado sube una nueva versión y quien devolvió no vuelve a revisar: el documento sigue con el siguiente revisor pendiente.
- Al completar el último paso el documento queda "aprobado para firma"; la subdirectora firma en físico y no tiene rol en el sistema.
- El encargado carga la versión firmada (solo PDF) desde la etapa, con sus datos (número y fecha); queda aprobada automáticamente y se crea el acto administrativo.
- Un usuario con dos permisos de revisor del mismo paso revisa una vez por cada permiso.
- Puedo consultar el historial de versiones y revisiones y la auditoría del documento.

### HU-CON-13 — Actos administrativos: Auto o Resolución
**Permiso:** `recurso_gestionar` (encargado de la etapa) / `recurso_super_gestion`
**Como** abogado encargado, **quiero** indicar si el acto que cargo es un Auto o una Resolución, con su número y fecha, **para** que el acto quede identificado como fue expedido.

**Criterios de aceptación:**
- Al cargar la versión final de un acto elijo la clase: AUTO o RES (Resolución).
- El número del acto es un entero de máximo 4 dígitos y la fecha de numerado es obligatoria; el sistema rechaza un número y fecha ya usados por otro acto del mismo tipo.
- Puedo corregir los datos del acto; eliminarlo solo lo puede hacer super gestión.
- Solo el encargado de la etapa (o super gestión) gestiona el acto.

### HU-CON-14 — Comunicación vs. notificación
**Permiso:** `recurso_gestionar` (encargado de la etapa)
**Como** abogado encargado, **quiero** registrar la comunicación o las notificaciones de cada acto según su tipo, **para** cumplir la forma de publicidad que exige cada actuación.

**Criterios de aceptación:**
- El auto que admite y el acto que reconoce al tercero interviniente **solo se comunican**: una comunicación por acto (número, fecha, fecha de envío y documento), y el sistema muestra la fecha en que se registró.
- Todos los demás actos **solo se notifican**: una notificación por cada solicitante o tercero vinculado, con la citación siempre obligatoria y, si fue exitosa, su tipo (personal, electrónica o aviso) y su documento.
- El sistema rechaza notificar un acto que solo se comunica y comunicar un acto que solo se notifica.
- No se puede notificar dos veces a la misma persona por el mismo acto.

### HU-CON-15 — Documentos anexos de cada etapa
**Permiso:** `recurso_gestionar`
**Como** abogado, **quiero** cargar documentos anexos en cada etapa del expediente, **para** conservar los soportes que llegan en la visita o después por radicado.

**Criterios de aceptación:**
- Cada etapa (auto que admite, concepto técnico, requerimiento, decisión, recurso, memorias, subsanación, recibo de obras e informes del usuario) tiene sus propios anexos; el tercero interviniente no tiene anexos.
- Cada anexo lleva un nombre (máximo 100 caracteres) y un PDF.
- Puedo cambiar el nombre, reemplazar el PDF o eliminar el anexo.

### HU-CON-16 — Consulta y descarga del expediente
**Permiso:** `recurso_consultar`
**Como** funcionario de consulta, **quiero** ver cualquier expediente de Concesiones en solo lectura y descargarlo completo, **para** consultarlo sin ir al archivo físico.

**Criterios de aceptación:**
- Puedo buscar expedientes por radicado, código del expediente, número VITAL, municipio, vereda o involucrado; el listado es paginado.
- Veo la información base, los involucrados y todas las etapas con sus documentos, sin formularios de edición.
- Puedo descargar el expediente completo en un único PDF con los documentos finales en el orden del trámite (sin las versiones en revisión).
- Quienes tienen `recurso_gestionar` o `recurso_super_gestion` también pueden consultar.

### HU-CON-17 — Mis informes de Concesiones
**Permiso:** `recurso_gestionar`, `recurso_tecnico` o cualquiera de los permisos de revisor de Concesiones
**Como** abogado, técnico o revisor, **quiero** ver en una sola lista los documentos que debo subir o revisar, **para** saber qué está pendiente de mi parte.

**Criterios de aceptación:**
- Veo solo mis documentos: aquellos de los que soy encargado y aquellos que me corresponde revisar o ya revisé; un líder no ve todo lo de su cadena.
- Puedo filtrar por rol (encargado o revisor), expediente (radicado o código), tipo de documento y estado, y marcar "solo los que requieren mi acción".
- Primero aparecen los que requieren mi acción, con la acción pendiente (por ejemplo, "Subir la versión corregida" o "Revisar el documento").
- La lista viene paginada (20 por página por defecto) y muestra el total y cuántos requieren acción.
- Desde cada fila abro el detalle del documento; el técnico carga allí su concepto firmado.

### HU-CON-18 — Super gestión: cargue histórico
**Permiso:** `recurso_super_gestion` (exige `recurso_gestionar`)
**Como** funcionario autorizado para el cargue histórico, **quiero** cargar directamente cualquier etapa de expedientes antiguos con su documento final y sus datos, **para** incorporar al sistema trámites que ya fueron aprobados en su momento.

**Criterios de aceptación:**
- Puedo cargar cualquier etapa omitiendo la revisión, el "Asignarme para diligenciar" y las validaciones de negocio; las reglas de la base de datos sí se aplican (campos obligatorios, datos repetidos).
- Todos los archivos deben ser PDF.
- El abogado encargado es opcional; si no lo elijo, la etapa queda sin encargado y su acto solo lo gestiona super gestión.
- Si elijo un abogado o un técnico, el sistema valida que tenga `recurso_gestionar` o `recurso_tecnico` según corresponda.
- Al cargar el acto de una etapa se cierra el proceso de revisión que estuviera abierto.

---
