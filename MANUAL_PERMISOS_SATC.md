# MANUAL DE PERMISOS — SISTEMA SATC

**Sistema de Administración de Trámites de Corpochivor**
**Actualizado:** 16 de octubre de 2026
**Audiencia:** administradores del sistema, coordinadores y soporte técnico

> Este manual describe los permisos tal como están definidos hoy en el sistema.
> La lista oficial de permisos, sus descripciones y sus dependencias vive en
> `app-users/db/permission_catalog.py` (ver sección 10).

---

## 1. CÓMO FUNCIONAN LOS PERMISOS Y LOS ROLES

- Un **permiso** abre una pantalla del menú, habilita acciones en el servidor, o
  ambas cosas. Algunos permisos no tienen pantalla propia: solo habilitan acciones
  (por ejemplo, revisar documentos o hacer cargue histórico).
- Un **rol** es un conjunto de permisos con un nombre (por ejemplo, "Abogado
  infracciones"). Cada usuario tiene **un** rol; al cambiar los permisos de un
  rol, cambian para todos los usuarios que lo tienen.
- El control es doble: aunque alguien escriba a mano la dirección de una
  pantalla, si no tiene el permiso el sistema lo devuelve al inicio, y el servidor
  rechaza la operación (error 403 "sin permisos").

### 1.1 Reglas de la pantalla "Roles y permisos"

- Un administrador **solo puede otorgar los permisos que su propio rol tiene**.
  La pantalla solo le muestra esos permisos y el servidor rechaza cualquier otro.
- Solo ve (y por tanto solo puede editar) los roles cuyos permisos tiene él
  mismo, y no puede eliminar un rol con permisos que no posee.
- Un rol **no se puede eliminar** mientras tenga usuarios asignados.
- Cada permiso muestra su **descripción** ("Desbloquea X. Sirve para Y."). La
  descripción es obligatoria (máximo 200 caracteres) y se puede editar en la
  pantalla de permisos.
- El nombre del rol admite máximo 20 caracteres.

### 1.2 Cuándo se ven reflejados los cambios

- Los servicios consultan los permisos del usuario en la base de datos y los
  guardan en memoria unos minutos (hasta 5). Un permiso quitado o agregado puede
  tardar ese tiempo en aplicarse en todos los módulos.
- El menú lateral se arma al cargar la aplicación. Después de cambiar un rol o
  el rol de un usuario, conviene que el usuario recargue la página o cierre
  sesión y vuelva a ingresar.
- El sistema permite una sola sesión activa por usuario: al iniciar sesión en
  otro equipo, la sesión anterior deja de ser válida.

---

## 2. MENÚ LATERAL DINÁMICO

El menú lateral se construye con los permisos del usuario. Cada permiso
pertenece a una **categoría** según el inicio de su nombre, y la categoría solo
aparece si el usuario tiene al menos un permiso de ella **con pantalla**.

| Categoría del menú       | Permisos cuyo nombre empieza por |
| ------------------------ | -------------------------------- |
| Administración           | `admin_`                         |
| Sancionatorio            | `sancionatorio_`                 |
| Infracciones             | `infraccion_`                    |
| Concesiones de Aguas     | `recurso_`                       |
| Documentos               | `documento_`                     |
| Involucrados             | `involucrado_`                   |
| Auditoría                | `auditoria_`                     |

Detalles del armado:

- Los permisos **sin ruta de menú** (marcados "—" en el catálogo) no generan
  entrada en el menú.
- **Infracciones:** `infraccion_informes_subir` e `infraccion_informes_revisar`
  llevan a la misma pantalla y se muestran como una sola entrada, **Mis informes**.
- **Concesiones de Aguas:** todos los permisos de revisor y el de técnico llevan
  a **Mis informes**, que aparece una sola vez. Quien tiene `recurso_gestionar`
  también ve Mis informes (allí suben sus documentos los abogados).
- Orden de las entradas: Gestionar → Consultar → Alertas → Asignar → Asignar
  informes → Mis informes (según lo que tenga cada usuario).

---

## 3. CATÁLOGO COMPLETO DE PERMISOS

El sistema tiene **32 permisos** en 7 categorías. La descripción es la misma que
ve el administrador en la pantalla de roles.

### 3.1 Administración

| Permiso                    | Ruta de menú    | Descripción |
| -------------------------- | --------------- | ----------- |
| `admin_roles_y_permisos`   | `/user/role`    | Desbloquea la pantalla Roles y permisos. Sirve para crear, editar y eliminar roles y permisos (solo puede otorgar permisos que su propio rol tenga). |
| `admin_registrar_usuarios` | `/user/add`     | Desbloquea la pantalla Registrar usuario. Sirve para crear cuentas de usuario y asignarles un rol. |
| `admin_gestionar_usuarios` | `/user/manage`  | Desbloquea la pantalla Gestionar usuarios. Sirve para editar datos, cambiar el rol y activar o desactivar usuarios. |

Notas: los usuarios no se eliminan, se desactivan. Al registrar o editar un
usuario, los nombres admiten máximo 20 caracteres y el correo máximo 100. Al
asignar un rol aplica la misma regla: no se puede dar un rol con permisos que el
administrador no tenga.

### 3.2 Sancionatorio

| Permiso                   | Ruta de menú           | Descripción |
| ------------------------- | ---------------------- | ----------- |
| `sancionatorio_gestionar` | `/file/manage`         | Desbloquea la pantalla Gestionar de sancionatorio. Sirve para crear y editar expedientes y diligenciar las etapas a su cargo. |
| `sancionatorio_consultar` | `/file/consult`        | Desbloquea la pantalla Consulta de sancionatorio. Sirve para ver cualquier expediente en solo lectura y descargarlo. |
| `sancionatorio_alertas`   | `/file/alerts`         | Desbloquea la pestaña Alertas de sancionatorio. Sirve para ver los vencimientos de sus expedientes o de todos. |
| `sancionatorio_asignar`   | `/file/assign_manage`  | Desbloquea la pantalla Asignar de sancionatorio. Sirve para asignar o cambiar el abogado responsable de un expediente. |

Solo aparecen como abogados asignables los usuarios con `sancionatorio_gestionar`.

### 3.3 Infracciones

| Permiso                       | Ruta de menú                 | Descripción |
| ----------------------------- | ---------------------------- | ----------- |
| `infraccion_gestionar`        | `/infraction/manage`         | Desbloquea la pantalla Gestionar de infracciones. Sirve para crear y editar expedientes y diligenciar las etapas a su cargo. |
| `infraccion_consultar`        | `/infraction/consult`        | Desbloquea la pantalla Consulta de infracciones. Sirve para ver cualquier expediente en solo lectura y descargarlo. |
| `infraccion_alertas`          | `/infraction/alerts`         | Desbloquea la pestaña Alertas de infracciones. Sirve para ver los vencimientos de sus expedientes o de todos. |
| `infraccion_asignar`          | `/infraction/assign_manage`  | Desbloquea la pantalla Asignar de infracciones. Sirve para asignar o cambiar el encargado responsable de un expediente. |
| `infraccion_asignar_informes` | `/infraction/reports`        | Desbloquea la pantalla Informes de infracciones. Sirve para asignar cada informe técnico a un profesional y a un revisor. |
| `infraccion_informes_subir`   | `/infraction/my-reports`     | Desbloquea Mis informes de infracciones. Sirve para subir los informes técnicos que le asignaron como profesional. |
| `infraccion_informes_revisar` | `/infraction/my-reports`     | Desbloquea Mis informes de infracciones. Sirve para revisar (aprobar o devolver) los informes técnicos que le asignaron como revisor. |
| `infraccion_super_gestion`    | —                            | Desbloquea el cargue manual de informes técnicos. Sirve para cargar informes históricos o manuales sin pasar por el flujo de revisión. |

Solo aparecen como encargados asignables los usuarios con `infraccion_gestionar`.
En la pantalla Informes solo se pueden elegir como profesional usuarios con
`infraccion_informes_subir` y como revisor usuarios con `infraccion_informes_revisar`.

### 3.4 Concesiones de Aguas

| Permiso                         | Ruta de menú           | Descripción |
| ------------------------------- | ---------------------- | ----------- |
| `recurso_gestionar`             | `/recurso/manage`      | Desbloquea la pantalla Gestionar de concesiones. Sirve para crear y editar expedientes, asignarse procesos y proyectar los documentos de cada etapa. |
| `recurso_consultar`             | `/recurso/consult`     | Desbloquea la pantalla Consulta de concesiones. Sirve para ver cualquier expediente en solo lectura y descargarlo completo. |
| `recurso_super_gestion`         | —                      | Desbloquea el cargue histórico de concesiones. Sirve para cargar directamente cualquier etapa de expedientes viejos sin revisión ni asignación. |
| `recurso_lider_juridico`        | `/recurso/my-reports`  | Desbloquea Mis informes de concesiones como líder jurídico. Sirve para revisar los actos administrativos en el primer paso de su cadena. |
| `recurso_lider_proyecto`        | `/recurso/my-reports`  | Desbloquea Mis informes de concesiones como líder del proyecto. Sirve para revisar tras el líder jurídico o técnico/SIG y aprobar para firma. |
| `recurso_asesora_subdireccion`  | `/recurso/my-reports`  | Desbloquea Mis informes de concesiones como asesora de subdirección. Sirve para revisar la decisión y el acto del recurso con el líder del proyecto. |
| `recurso_lider_tecnico`         | `/recurso/my-reports`  | Desbloquea Mis informes de concesiones como líder técnico. Sirve para revisar los conceptos técnicos. |
| `recurso_sig`                   | `/recurso/my-reports`  | Desbloquea Mis informes de concesiones como SIG. Sirve para revisar el concepto técnico de la etapa 2 junto con el líder técnico. |
| `recurso_tecnico`               | `/recurso/my-reports`  | Desbloquea Mis informes de concesiones como técnico. Sirve para que el abogado lo elija como técnico y cargar su concepto técnico. |

Detalle en la sección 6.

### 3.5 Documentos (flujo genérico de revisión)

| Permiso               | Ruta de menú        | Descripción |
| --------------------- | ------------------- | ----------- |
| `documento_gestionar` | `/document/manage`  | Desbloquea el módulo de Documentos. Sirve para ver y gestionar los documentos del flujo genérico de revisión. |
| `documento_crear`     | —                   | Desbloquea la creación en el módulo de Documentos. Sirve para cargar documentos y sus nuevas versiones en el flujo genérico de revisión. |
| `documento_revisar`   | —                   | Desbloquea la revisión en el módulo de Documentos. Sirve para aprobar o devolver documentos en el flujo genérico de revisión. |

Solo pueden elegirse como revisores de un documento los usuarios con
`documento_revisar`. Este módulo es independiente de los informes técnicos de
Infracciones y de los documentos de Concesiones de Aguas, que tienen su propio
flujo de revisión dentro de cada módulo.

### 3.6 Involucrados

| Permiso                 | Ruta de menú        | Descripción |
| ----------------------- | ------------------- | ----------- |
| `involucrado_gestionar` | `/involved/manage`  | Desbloquea el módulo de Involucrados. Sirve para registrar y editar las personas naturales o jurídicas vinculadas a los expedientes. |

### 3.7 Auditoría (solo lectura)

| Permiso                  | Ruta de menú          | Descripción |
| ------------------------ | --------------------- | ----------- |
| `auditoria_usuarios`     | `/audit/users`        | Desbloquea la auditoría de usuarios. Sirve para consultar el historial de cambios en usuarios, roles y permisos. |
| `auditoria_expedientes`  | `/audit/files`        | Desbloquea la auditoría de sancionatorio. Sirve para consultar el historial de cambios en los expedientes sancionatorios. |
| `auditoria_involucrados` | `/audit/involved`     | Desbloquea la auditoría de involucrados. Sirve para consultar el historial de cambios en los involucrados. |
| `auditoria_infracciones` | `/audit/infractions`  | Desbloquea la auditoría de infracciones. Sirve para consultar el historial de cambios en los expedientes de infracción. |

---

## 4. DEPENDENCIAS OBLIGATORIAS ENTRE PERMISOS

Algunos permisos **exigen** tener otro en el mismo rol. La dependencia va en un
solo sentido: tener el permiso requerido no obliga a tener el dependiente.

| Si el rol tiene...               | ...debe tener también    |
| -------------------------------- | ------------------------ |
| `sancionatorio_alertas`          | `sancionatorio_consultar` |
| `sancionatorio_asignar`          | `sancionatorio_consultar` |
| `infraccion_alertas`             | `infraccion_consultar`    |
| `infraccion_asignar`             | `infraccion_consultar`    |
| `infraccion_asignar_informes`    | `infraccion_consultar`    |
| `infraccion_informes_subir`      | `infraccion_consultar`    |
| `infraccion_informes_revisar`    | `infraccion_consultar`    |
| `infraccion_super_gestion`       | `infraccion_gestionar`    |
| `documento_crear`                | `documento_gestionar`     |
| `documento_revisar`              | `documento_gestionar`     |
| `recurso_super_gestion`          | `recurso_gestionar`       |
| `recurso_tecnico`                | `recurso_consultar`       |
| `recurso_lider_juridico`         | `recurso_consultar`       |
| `recurso_lider_proyecto`         | `recurso_consultar`       |
| `recurso_asesora_subdireccion`   | `recurso_consultar`       |
| `recurso_lider_tecnico`          | `recurso_consultar`       |
| `recurso_sig`                    | `recurso_consultar`       |

### 4.1 Comportamiento de la pantalla de roles

- Un permiso dependiente aparece **bloqueado** (no se puede marcar) mientras no
  esté marcado el permiso que requiere; debajo se indica "Requiere: …".
- Al **desmarcar** un permiso requerido, se desmarcan automáticamente los
  permisos que dependen de él, y la pantalla avisa cuáles se quitaron.
- El botón "Todos" de una categoría marca primero los requeridos y luego sus
  dependientes; los que exigen un permiso de otra categoría que no esté marcado
  quedan sin marcar.
- Si un rol (por ejemplo, uno creado antes de existir estas reglas) tiene un
  permiso sin su requerido, la pantalla lo lista y **no deja guardar** hasta
  corregirlo.

### 4.2 Validación en el servidor

- Al crear o editar un rol, el servidor **rechaza** el guardado si no cumple las
  dependencias e indica qué falta (por ejemplo: «infraccion_alertas» requiere
  «infraccion_consultar»).
- Los roles que ya existían y no cumplen **siguen funcionando** igual; solo se
  exige la regla cuando se vuelven a guardar.
- Para conocer esos roles hay un reporte de solo lectura (para soporte técnico,
  no tiene pantalla): `GET /users/role/dependencias-incumplidas`, que exige
  `admin_roles_y_permisos` y lista cada rol con los permisos que le faltan.
  Además, al arrancar, app-users deja esos roles anotados en su log.

---

## 5. REGLAS DE ALCANCE: QUÉ EXPEDIENTES VE Y MODIFICA CADA USUARIO

### 5.1 Sancionatorio e Infracciones

- **Consultar** (`sancionatorio_consultar` / `infraccion_consultar`): ve
  **cualquier** expediente, en solo lectura, y lo puede descargar.
- **Gestionar** (`sancionatorio_gestionar` / `infraccion_gestionar`): solo
  modifica (y, sin permiso de consulta, solo ve) los expedientes de los que es
  **abogado responsable / encargado**. Para ver expedientes ajenos necesita
  también el permiso de consultar.
- **Asignar**: cambia el responsable de los expedientes; solo puede elegir
  usuarios con el permiso de gestionar del mismo módulo.

### 5.2 Pestaña Alertas (Sancionatorio e Infracciones)

- La pestaña se abre con el permiso de alertas del módulo
  (`sancionatorio_alertas` / `infraccion_alertas`), que a su vez exige el de
  consultar.
- Tiene un filtro **"Mis expedientes / Todos"**:
  - **Mis expedientes** (por defecto): vencimientos de los expedientes de los que
    el usuario es responsable.
  - **Todos**: vencimientos de todos los expedientes. El servidor solo lo
    entrega a quien tiene el permiso de alertas del módulo.
- Cada alerta enlaza a **Gestionar** si el usuario es el responsable de ese
  expediente, o a **Consultar** si no lo es. En la vista "Todos" cada alerta se
  marca como "Mío" u "Otro responsable".

### 5.3 Concesiones de Aguas

- **Consultar** (`recurso_consultar`): ve cualquier expediente en solo lectura y
  descarga el expediente completo. Gestionar y super gestión también pueden
  consultar.
- **Gestionar** (`recurso_gestionar`): crea y edita la información base de los
  expedientes. En cada etapa, el abogado usa **"Asignarme para diligenciar"** y
  desde ese momento solo él (el encargado) gestiona el documento de esa etapa.
- Los permisos de revisor y de técnico solo dan acceso a **Mis informes** y a la
  consulta (por eso exigen `recurso_consultar`).

---

## 6. CONCESIONES DE AGUAS: ROLES DE REVISIÓN

Los documentos que se proyectan en Concesiones de Aguas pasan por una **cadena
de revisión** según el tipo de documento. Cada paso lo deben revisar **todas**
las personas del paso (en cualquier orden) antes de avanzar al siguiente. El
sistema envía cada documento a quienes tengan el permiso de revisor del paso
pendiente y se les muestra en **Mis informes**.

| Documento | Lo sube | Paso 1 | Paso 2 |
| --------- | ------- | ------ | ------ |
| Auto que admite, requerimiento, acto que aprueba las memorias | Abogado encargado | Líder jurídico | Líder del proyecto |
| Decisión, acto que resuelve el recurso | Abogado encargado | Líder jurídico | Líder del proyecto **y** asesora de subdirección |
| Acto que reconoce al tercero interviniente, acto que aprueba las obras | Abogado encargado | Líder jurídico | Líder del proyecto |
| Concepto técnico (etapa 2) | Técnico seleccionado | Líder técnico **y** SIG | Líder del proyecto |
| Concepto adicional, de memorias, de subsanación, de obras y segundo de obras | Técnico seleccionado | Líder técnico | — |

> Las cadenas del acto que reconoce al tercero y del acto que aprueba las obras
> son **provisionales** (pendientes de confirmar con el área jurídica).

Reglas del flujo:

1. Si un revisor **devuelve** el documento, el encargado sube una nueva versión.
   Quien devolvió no vuelve a revisar: al subir la corrección, el documento sigue
   con el siguiente revisor pendiente.
2. Al completar el último paso queda **aprobado para firma**. La siguiente
   versión que sube el encargado (en PDF) es la firmada y queda aprobada
   automáticamente.
3. La **subdirectora firma en físico y no tiene rol en el sistema**.
4. Un usuario con dos permisos de revisor del mismo paso revisa una vez por cada
   permiso.

Otros roles:

- **Técnico** (`recurso_tecnico`): solo los usuarios con este permiso aparecen
  cuando el abogado elige el técnico encargado de un concepto técnico. El técnico
  sube su concepto desde Mis informes.
- **Abogado** (`recurso_gestionar`): proyecta y sube los actos de las etapas que
  se asignó, y los ve en Mis informes.

---

## 7. SUPER GESTIÓN (CARGUE HISTÓRICO)

Son permisos especiales para cargar expedientes viejos, cuyos documentos ya
fueron aprobados en su momento. Se recomienda otorgarlos a muy pocas personas.

### 7.1 Infracciones — `infraccion_super_gestion`

(Antes se llamaba `infraccion_cargue`; el cambio de nombre conservó los roles
que lo tenían.) Exige `infraccion_gestionar`. Permite:

- Cargar informes técnicos de forma **manual** (históricos), sin pasar por el
  flujo de asignación y revisión, eligiendo de forma opcional profesional y
  revisor.
- Cambiar el modo de cargue de un informe (manual o por flujo). Antes de
  confirmar, el sistema muestra qué etapas posteriores del expediente se
  borrarían.
- Diligenciar la matriz de un informe cargado en modo manual.
- Crear el informe de seguimiento sin esperar a que venza el término del
  concepto técnico.

### 7.2 Concesiones de Aguas — `recurso_super_gestion`

Exige `recurso_gestionar`. Permite cargar directamente **cualquier etapa** de un
expediente con su documento final y sus datos, **omitiendo** la revisión, el
"Asignarme para diligenciar" y las validaciones de negocio. Las reglas de la
base de datos sí se aplican (campos obligatorios, datos repetidos). Todos los
archivos deben ser PDF.

---

## 8. FLUJOS DE TRABAJO Y PERMISOS NECESARIOS

### 8.1 Sancionatorio

```
Coordinador (sancionatorio_asignar + sancionatorio_consultar)
    └─ Asigna el expediente a → Abogado (sancionatorio_gestionar)
                                   └─ Diligencia las etapas de sus expedientes
Consulta (sancionatorio_consultar)
    └─ Ve y descarga cualquier expediente, sin modificar
```

### 8.2 Infracciones con informes técnicos

```
Coordinador (infraccion_asignar + infraccion_asignar_informes + infraccion_consultar)
    ├─ Asigna el expediente a → Abogado (infraccion_gestionar)
    └─ Asigna cada informe técnico a:
          ├─ Profesional (infraccion_informes_subir + infraccion_consultar) → lo sube en Mis informes
          └─ Revisor    (infraccion_informes_revisar + infraccion_consultar) → lo aprueba o lo devuelve
```

### 8.3 Concesiones de Aguas

```
Abogado (recurso_gestionar) → "Asignarme" en la etapa → proyecta el acto
    └─ Revisión: líder jurídico → líder del proyecto (+ asesora en decisión/recurso)
    └─ Aprobado para firma → firma física → el abogado sube la versión firmada
Abogado elige técnico (recurso_tecnico) → el técnico sube el concepto
    └─ Revisión: líder técnico (+ SIG y líder del proyecto en la etapa 2)
```

### 8.4 Documentos (flujo genérico)

```
Creador (documento_gestionar + documento_crear) → carga el documento y elige revisores
Revisor (documento_gestionar + documento_revisar) → aprueba o devuelve
```

---

## 9. PERFILES DE ROL SUGERIDOS

Ejemplos coherentes con las dependencias de la sección 4. Ajústelos al cargo
real de cada persona.

### Abogado sancionatorio
`sancionatorio_gestionar`, `sancionatorio_consultar`, `sancionatorio_alertas`,
`involucrado_gestionar`

### Abogado infracciones
`infraccion_gestionar`, `infraccion_consultar`, `infraccion_alertas`,
`involucrado_gestionar`

### Abogado de Concesiones de Aguas
`recurso_gestionar`, `recurso_consultar`, `involucrado_gestionar`

### Solo consulta
`sancionatorio_consultar`, `infraccion_consultar`, `recurso_consultar`
(según los módulos que deba ver)

### Gerente / supervisor (alertas de todos los expedientes)
`sancionatorio_consultar`, `sancionatorio_alertas`, `sancionatorio_asignar`,
`infraccion_consultar`, `infraccion_alertas`, `infraccion_asignar`,
`infraccion_asignar_informes`, `auditoria_expedientes`, `auditoria_infracciones`

Con el permiso de alertas puede usar el filtro "Todos"; si no es responsable de
un expediente, la alerta lo lleva a Consultar.

### Técnico de infracciones (sube informes)
`infraccion_consultar`, `infraccion_informes_subir`

### Revisor de informes técnicos de infracciones
`infraccion_consultar`, `infraccion_informes_revisar`

### Técnico de Concesiones de Aguas
`recurso_consultar`, `recurso_tecnico`

### Revisores de Concesiones de Aguas
Siempre `recurso_consultar` más el permiso del cargo:

| Cargo                     | Permiso adicional               |
| ------------------------- | ------------------------------- |
| Líder jurídico            | `recurso_lider_juridico`        |
| Líder del proyecto        | `recurso_lider_proyecto`        |
| Asesora de subdirección   | `recurso_asesora_subdireccion`  |
| Líder técnico             | `recurso_lider_tecnico`         |
| SIG                       | `recurso_sig`                   |

### Cargue histórico
- Infracciones: `infraccion_gestionar`, `infraccion_consultar`, `infraccion_super_gestion`
- Concesiones: `recurso_gestionar`, `recurso_consultar`, `recurso_super_gestion`

### Documentos
- Creador: `documento_gestionar`, `documento_crear`
- Revisor: `documento_gestionar`, `documento_revisar`

### Administrador
Los 32 permisos. El sistema crea el rol `admin` con todos los permisos al
instalarse por primera vez, y cada permiso nuevo del catálogo se agrega
automáticamente a los roles que ya tenían todos los permisos.

---

## 10. NOTA PARA EL EQUIPO TÉCNICO: SINCRONIZACIÓN DEL CATÁLOGO

- Los permisos se definen en `app-users/db/permission_catalog.py`:
  `PERMISOS` (nombre, ruta de menú y descripción), `DEPENDENCIAS` y `RENOMBRES`.
- Cada vez que arranca app-users se sincroniza el catálogo con la base de datos
  (`db/permission_sync.py`), sin SQL manual en la VM:
  - Crea los permisos nuevos y los otorga a los roles que tenían todos los
    permisos (superadministradores).
  - Llena la ruta de menú y la descripción **solo si están vacías**: lo editado
    desde la pantalla de permisos no se pisa. Cambiar una descripción en el
    catálogo no modifica la que ya existe en la base.
  - Aplica los **renombres** sobre la misma fila, así los roles conservan el
    permiso (ejemplo: `infraccion_cargue` → `infraccion_super_gestion`).
  - Deja la tabla de dependencias igual a `DEPENDENCIAS`.
  - Nunca borra permisos ni corrige roles; solo informa en el log los que
    incumplen dependencias.
- La descripción es obligatoria (máx. 200 caracteres) y editable desde la
  pantalla de permisos.
- Los servicios validan los permisos **por su nombre**. No cambie el nombre ni
  elimine desde la pantalla un permiso del catálogo: el servicio dejaría de
  reconocerlo y, al reiniciar app-users, el permiso del catálogo se volvería a
  crear. Los cambios de nombre se hacen agregándolos a `RENOMBRES`.

---

_Documento elaborado a partir del código fuente de `app-users`,
`app-sancionatoria`, `app-infraction`, `app-recurso`, `app-docs`, `app-involved`
y el frontend del sistema SATC (octubre de 2026)._
