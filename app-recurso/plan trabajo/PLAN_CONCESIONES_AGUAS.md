# Plan de trabajo — Microservicio Concesiones de Aguas Superficiales (CA)

> Documento para Claude Code. Describe el proceso de negocio, las reglas y el orden de implementación.
> Fuente: reuniones con el área jurídica de Recurso Hídrico (24/09/2026 y 25/09/2026), la base Excel `CA 2026` y decisiones del equipo.
> **Regla para quien implemente:** si algo no está en este documento, NO lo inventes. Márcalo como `TODO(negocio)` y pregunta.

---

## 0. Contexto y alcance

- Microservicio nuevo, hermano de **sancionatorio** e **infracciones (infraction)**. Reutiliza sus patrones; cuando este plan diga "como en el proceso hermano", revisa esa implementación antes de escribir código nuevo.
- Modelo de datos de referencia: `concesiones_dbml.txt` (DBML).
- **Integraciones externas** (no se crean tablas para esto):
  - **app-users**: funcionarios (abogados, técnicos, líderes). Los campos `encargado_acto_id` y `tecnico_encargado_id` guardan solo el id.
  - **app-involved**: personas externas (solicitantes, terceros intervinientes, representantes legales). Los campos `involucrado_id` y `representante_id` guardan solo el id.
  - **app-docs**: solo **almacena** archivos (cargue, hash, validación de virus, etc.). Todo campo `doc_*_id` apunta a un archivo de app-docs.
- **Documentos dentro de esta app:** el proceso de cargue, versiones y revisiones de cada documento vive en este microservicio, igual que en el cambio reciente de **infraction-app**. Replicar su modelo y lógica (ver §5).
- **Stack:** pendiente de confirmar. Recomendación: Python, igual que el resto de apps. La concurrencia se resuelve en la base de datos (ver §7).
- **Fuera de alcance por ahora:** POEA, prórroga/modificación/cancelación, plazos y alertas, seguimiento (lo hace Secretaría General en otro sistema).

---

## 1. Pestañas

| Pestaña | Permiso | Qué hace | Referencia |
|---|---|---|---|
| **Gestionar** | `recurso_gestionar` | Crear y modificar expedientes, vincular involucrados, asignarse procesos ("Asignarme para diligenciar") y proyectar/cargar los documentos de cada etapa. | Pestaña equivalente de sancionatorio/infracciones. |
| **Consulta** | `recurso_consultar` | Ver el expediente completo (todas las etapas y soportes) y **descargar el expediente completo**. | Equivalente a consulta de sancionatorio/infracciones. |
| **Mis informes** | Cualquier usuario con un documento a cargo | Gestionar los documentos que la persona debe **subir** (es encargado o técnico asignado) o **revisar** (por su rol de revisor). | "Mis informes" de los procesos hermanos. |

---

## 2. Permisos y roles

| Permiso | Tipo | Para qué |
|---|---|---|
| `recurso_gestionar` | Acceso | Desbloquea la pestaña Gestionar y sus funciones. También protege los endpoints de escritura. **Solo** quien lo tenga puede crear, editar o proyectar. |
| `recurso_consultar` | Acceso | Desbloquea la pestaña Consulta (solo lectura y descarga). |
| `recurso_super_gestion` | Acceso especial | Superusuario para **cargue histórico** (ver §2.1). |
| `recurso_lider_juridico` | Revisor | Revisa los actos administrativos. |
| `recurso_lider_proyecto` | Revisor | Revisa después del líder jurídico (y del líder técnico/SIG en conceptos). Marca "aprobado para firma". |
| `recurso_asesora_subdireccion` | Revisor | Revisa la **decisión** y el **acto del recurso**, junto con el líder del proyecto. |
| `recurso_lider_tecnico` | Revisor | Revisa todos los conceptos técnicos. |
| `recurso_sig` | Revisor | Revisa el concepto técnico de la etapa 2, junto con el líder técnico. |
| `recurso_tecnico` | Selección | Personas que el abogado puede seleccionar como técnico encargado de un concepto técnico. |

**Reglas:**
1. Los permisos de revisor sirven para la lógica de negocio: el sistema enruta cada revisión a quien tenga ese permiso y le aparece en "Mis informes".
2. La **subdirectora** firma en físico y **no tiene rol en el sistema**. Lo único que llega al sistema es la versión firmada.

### 2.1 Super gestión (`recurso_super_gestion`)
- Propósito: cargar **expedientes viejos** cuyos documentos ya fueron aprobados en su momento.
- Puede tocar **cualquier etapa** y subir información **omitiendo** el flujo de revisión, la asignación ("Asignarme") y las validaciones de §6.
- Se le facilitan formularios de cargue directo (documento final + datos de cada etapa). Tomar como referencia el cargue del proceso **infraction**.
- Las restricciones de integridad de la base de datos (`unique`, `not null`, FKs) **sí** aplican.

---

## 3. Información base (nacimiento del expediente)

**Regla de nacimiento:** el expediente se crea cuando llega el **comprobante de pago**. Antes de eso el trámite es una PQR y **no entra al sistema**. Los requerimientos de la PQR y los valores de la factura no hacen parte del expediente.

**Datos de nacimiento:** son los campos de la tabla `expediente`.

| Campo | Regla |
|---|---|
| `radicado`, `fecha_radicado` | Radicado del expediente y su fecha. Único. |
| `expediente` (`CA 001-26`) | Único. Identificador del expediente para siempre (las prórrogas o modificaciones siguen en el mismo). |
| `radicado_oficio_entrada`, `fecha_oficio_entrada` | Radicado de la **solicitud** del solicitante y su fecha. Su documento es el comprobante de pago (`doc_comprobante_pago_id`). |
| `doc_comprobante_pago_id` | PDF del comprobante de pago. |
| `numero_vital` | Obligatorio. |
| `nombre_predio`, `matricula_inmobiliaria`, `codigo_catastral` | Obligatorios. Salen del certificado de tradición y libertad. |
| `vereda_id` (→ municipio) | Catálogo. |
| `tipo_fuente_id` | Catálogo `tipo_fuente` (ver §3.1). |
| Fuentes (`expediente_fuente`) | Catálogo `fuente` (quebrada, río, nacimiento…). Un expediente puede tener varias. |
| `nombre_fuente` | Texto libre, `varchar(50)`. Nombre propio de la fuente (p. ej. "Juancho Castro"). |
| Usos (`expediente_uso`) | Enum `uso_agua` (ver §3.1). Un expediente puede tener varios. |

**Involucrados (`expediente_involucrado`, datos en app-involved):**
1. Los solicitantes se **vinculan y desvinculan** del expediente igual que los "posibles infractores" en los procesos hermanos.
2. Puede haber **más de un** solicitante.
3. Si el involucrado es empresa (tipo de documento **NIT**), es obligatorio vincular su **representante legal** (`representante_id`).
4. El **tercero interviniente** se vincula en la misma tabla con `tipo_vinculo = TERCERO_INTERVINIENTE` (ver §4, transversal).

### 3.1 Datos semilla (seed)

Valores sacados de todas las hojas del Excel (CA 1996 a CA 2026), normalizados: se unieron errores de digitación, tildes y plurales, y se separaron las celdas con varios valores.

**Municipios y veredas:** misma estructura y mismos valores de los procesos hermanos. Copiar su seed.

**`tipo_fuente`** (tabla):

| Valor | Variantes encontradas en el Excel |
|---|---|
| SUPERFICIAL | SUPERFICIALES, SUPERFCIAL, SUPERCIAL, SUPERICIAL, SSUPERFICIAL… (≈1.190 registros) |
| LÓTICO | LOTICO, LOTICOS, LOTOCO, SUPERFICIAL - LÓTICO (≈30) |
| LÉNTICO | LENTICO, SUPERFICIAL LÉNTICO (4) |
| SUBTERRÁNEO | SUBTERRANEO (1) |

**`fuente`** (tabla):

| Valor | Variantes encontradas en el Excel |
|---|---|
| NACIMIENTO | NACIEMIENTO, NACIMEINTO, NACIMINETO, NACIMIEN TO, NACIMIENTOS… |
| QUEBRADA | QUEBRADAS, QUEBRADA0 |
| RÍO | RIO |
| MANANTIAL | MANATIAL |
| CAÑADA | |
| CAÑO | |
| CHORRO | |
| AFLUENTE | |
| ALJIBE | ALGIBE, ALJIBES |
| RESERVORIO | RESERVORIO ARTIFICIAL |
| OJO DE AGUA | |
| NACEDERO | |
| LAGUNA | |
| LAGO | |
| ZANJA | SANJA |
| AGUAS LLUVIAS | |
| AGUAS DE DRENAJE | DRENAJE INTERMITENTE |
| AGUAS DE INFILTRACIÓN | |
| AGUAS RESIDUALES | |

No se incluyen los valores que en realidad son nombres propios mal ubicados en la columna (TURMEQUÉ, TIBANÁ, SAN JOSÉ, RISATA, EL ESPINO, etc.), ni "SIN NOMBRE", "NA" o "SIN ESTABLECER". Esos nombres corresponden a `nombre_fuente`.

**`uso_agua`** (enum):

| Valor | Variantes encontradas en el Excel |
|---|---|
| DOMESTICO | DOMÉSTICO, USO DOMÉSTICO, ABASTECIMIENTO DOMÉSTICO, DOMESTIO, DOSMESTICO… |
| PECUARIO | OECUARIO, PECURIO, BOVINOS, AVÍCOLA, PORCÍCOLA, AGROPECUARIO |
| ABREVADERO | ABREVADEROS, ABREBADERO, ABREVAERO… |
| AGRICOLA | AGRÍCOLA, AGRÍCOLAS, HORTALIZAS, CULTIVO DE PAPA |
| RIEGO | RIIEGO, RIEGO GOTEO Y ASPERSIÓN, RIEGO (VIVERO) |
| INDUSTRIAL | INDUSTRIAL (MINERÍA), (EMBOTELLAMIENTO), (LAVADERO DE CARROS), LAVADO DE ZANAHORIA, VENTA DE ALIMENTOS |
| ACUICULTURA | PISCÍCOLA, PISCICULTURA, ACUICULTURA Y PESCA |
| SILVICULTURA | |
| RECREATIVO | RECREACIONAL, RECREACIÓN Y DEPORTES, RECREATIVA (RESTAURANTE, HOTELERO, PISCINA) |
| INSTITUCIONAL | ADMINISTRACIÓN PÚBLICA Y DEFENSA |
| OTRO | OTROS (EMERGENCIAS), RIEGO DE VÍAS |

`TODO(negocio)`: la agrupación de variantes (por ejemplo, AVÍCOLA dentro de PECUARIO o PISCÍCOLA dentro de ACUICULTURA) es una propuesta para migrar datos viejos. Validarla con el área.

**`tipo_notificacion`** (tabla): PERSONAL, ELECTRÓNICA, AVISO.

---

## 4. Etapas: orden, sub-etapas y condiciones de creación

### Orden general

```
INFORMACIÓN BASE
  └─ ETAPA 1 · Auto que admite                   (obligatoria)
       ├─ ETAPA 2 · Concepto técnico             (obligatoria salvo desistimiento)
       │    └─ ETAPA 3 · Requerimiento           (opcional)
       │         └─ Sub: Concepto técnico adicional (opcional, sin visita)
       └─ ETAPA 4 · Decisión del proceso         (obligatoria)
            ├─ Sub: Citación y notificación
            ├─ Sub: Recurso de reposición        (opcional)
            │    └─ Sub: Acto que resuelve el recurso + notificación
            ├─ ETAPA 5 · Memorias de cálculo     (solo si OTORGADA y requiere planos)
            └─ ETAPA 6 · Recibo a satisfacción de obras (siempre que sea OTORGADA)

Transversal: Tercero interviniente (opcional, en cualquier momento)
```

### Reglas comunes a todas las etapas

**A. Asignación ("Asignarme para diligenciar")**
1. La asignación del líder jurídico es **verbal** y no tiene implicación en el aplicativo.
2. El abogado (con `recurso_gestionar`) entra al proceso y usa **"Asignarme para diligenciar"**. Su id queda en `encargado_acto_id`.
3. Desde ese momento **solo él** puede gestionar ese proceso específico.
4. Si el proceso ya tiene encargado, nadie más puede tomarlo. **No hay reasignación.**
5. La asignación debe ser atómica (ver §7): `UPDATE ... SET encargado_acto_id = :yo WHERE id = :id AND encargado_acto_id IS NULL`; si no actualiza filas → 409 "Ya fue asignado".

**B. Técnico encargado**
- El abogado **selecciona** el técnico encargado de un concepto entre los usuarios con `recurso_tecnico`.
- El técnico seleccionado solo puede cargar el concepto que tiene asignado.

**C. Datos que salen de un documento**
- Quien sube un documento firmado diligencia los datos que vienen escritos en él. Ejemplo: la líder técnica define técnico y fecha de visita, eso queda escrito en el auto admite, y es el **abogado** quien los registra en el aplicativo al subir el auto firmado.

**D. Patrón etapa vs. sub-proceso (modelo de datos)**
- Una tabla guarda `expediente_id` (único y nullable) solo cuando **es** la etapa directa (p. ej. `concepto_tecnico` = etapa 2, `requerimiento` = etapa 3).
- Cuando la misma tabla se usa como sub-proceso de otra etapa (memorias, subsanación, recibo de obras), la referencia el padre por id y su `expediente_id` queda en `NULL`.

**E. Ciclo de vida de una etapa con acto administrativo**
1. Se crea la fila de la etapa al **asignarse** el abogado (`encargado_acto_id`).
2. El documento se proyecta y revisa **en esta app** (§5); los archivos se almacenan en app-docs.
3. Al subir la versión firmada y **numerarse**, se crea el `acto_administrativo` (número + fecha de numerado obligatorios) y se enlaza en `acto_admin_id` (por eso es nullable en la etapa).
- El documento en proyección se enlaza con la etapa igual que en **infraction-app**.

---

### ETAPA 1 · Auto que admite (`acto_admite`)

**Condición de creación:** existe el expediente.

**Flujo:**
1. Un abogado se asigna el auto admite.
2. Proyecta el paquete: auto, comunicación al solicitante, aviso para fijar en la corporación y oficio a la Alcaldía.
3. Revisión jurídica estándar (§5). Firma la subdirectora en físico.
4. La líder técnica define técnico y fecha de visita, que quedan escritos en el auto y en el aviso.
5. El abogado sube el auto **firmado y numerado** y en ese mismo momento diligencia **fecha de visita técnica** y **técnico** (seleccionado entre `recurso_tecnico`). Con eso **nace la etapa 2**.
6. Se comunica (una comunicación por acto, pública, no por persona) y se envía a la Alcaldía. El aviso se fija **10 días hábiles** en la corporación. El auto que admite **solo se comunica, no se notifica** (aclaración del área, 13/10/2026).
7. Después se carga la **constancia de fijación de la Alcaldía**.

**Documentos:** auto, oficio a la Alcaldía, fijación del aviso corporativo, constancia de fijación de la Alcaldía (nullable: llega después).

**Reglas:**
- Sin auto admite **no puede existir ninguna** etapa siguiente.
- La fecha de visita debe ser posterior al desfijado del aviso. Lo garantiza la norma; no es necesario validarlo.

---

### ETAPA 2 · Concepto técnico (`concepto_tecnico`, con `expediente_id`)

**Condición de creación:** el auto admite registró fecha de visita y técnico.

**Flujo:**
1. El técnico asignado hace la visita y proyecta el concepto.
2. Revisan el líder técnico y el **SIG** (en cualquier orden) y luego el líder del proyecto.
3. El técnico carga la versión firmada y diligencia: fecha del concepto (= fecha de firma), caudal fuente, caudal disponible, caudal otorgado y número de usuarios.
4. Los **documentos opcionales** (`documentos_anexos`) los carga el **abogado**. Pueden llegar en la visita o después por radicado.

`TODO(negocio)`: confirmar con el líder técnico si los 4 datos de caudal son suficientes.

---

### ETAPA 3 · Requerimiento (`requerimiento`, con `expediente_id`) — OPCIONAL

**Condición de creación:** existe el concepto técnico de la etapa 2 con fecha de concepto.

**Cuándo sale:** el concepto dice que se puede otorgar pero falta algo (p. ej. copia de la cédula). Si no falta nada, se pasa directo a la decisión.

**Flujo:**
1. Un abogado se asigna el requerimiento.
2. Revisión jurídica estándar (§5) y versión firmada y numerada.
3. **Se notifica** (citación y notificación).
4. El usuario responde con un radicado (oficio de entrada + PDF).

**Sub-proceso: concepto técnico adicional** — opcional y poco frecuente.
- Solo si la respuesta del usuario hay que reevaluarla.
- El abogado selecciona el técnico. Igual al concepto de la etapa 2 pero **sin visita**. Lo revisa el líder técnico.
- Se guarda en `concepto_tecnico` con `expediente_id = NULL`, referenciado desde `requerimiento.concepto_tecnico_id`.

---

### ETAPA 4 · Decisión del proceso (`decision`)

**Condición de creación:**
- Existe el auto admite.
- Existe la **constancia de fijación de la Alcaldía**.
- **No** requiere concepto técnico: si el usuario desiste, se decide sin concepto.

**Flujo:**
1. Un abogado se asigna la decisión.
2. Revisión de decisión (§5): líder jurídico → líder del proyecto **y** asesora de subdirección.
3. Firma la subdirectora en físico; el abogado sube la versión firmada y numerada.
4. Se notifica.

**Reglas:**
- La decisión es **OTORGADA, NEGADA o DESISTIDA** y se toma **una sola vez** por expediente.
- `requiere_memorias` solo puede ser `true` si la decisión es OTORGADA (la decisión exige planos y no solo medidor o llave).
- **Fecha de ejecutoria:** 10 días hábiles después de notificar si no hay recurso. Si hay recurso, cuando queda en firme.

**Sub: Citación y notificación** (`notificacion`, una fila por persona notificada)
1. **Siempre se cita.** Después la persona puede pedir notificación electrónica, pero la citación igual existe; por eso los campos de citación son obligatorios.
2. La citación da 10 días; luego se notifica (personal, electrónica o por aviso).
3. Se registra si fue exitosa y su forma.
- Se notifica a cada solicitante y a cada tercero interviniente.

**Sub: Recurso de reposición** (`recurso_reposicion`) — OPCIONAL
- **Condición:** existe el acto de decisión notificado.
- El usuario lo radica dentro de los 10 días hábiles siguientes a la notificación.
- Se crea primero con el radicado y el PDF; el acto que lo resuelve (`acto_admin_id`, `resultado`) se agrega después.
- Acto que resuelve: un abogado se lo asigna; misma revisión que la decisión. Resultado: REPONE, CONFIRMA, MODIFICA o ADICIONA. Se notifica.

---

### ETAPA 5 · Memorias de cálculo (`memorias_calculo`) — OPCIONAL

**Condición de creación:** decisión OTORGADA **y** `requiere_memorias = true`. Si solo exige medidor o llave, no existe y se pasa a la etapa 6.

**Flujo (un ciclo):**
1. Se registra el radicado de los planos del usuario (radicado + PDF).
2. **Concepto técnico sin visita**: el abogado selecciona el técnico; lo revisa y firma **solo la líder técnica**. El técnico registra **Cumple / No cumple**.
3. Si **No cumple** → **requerimiento** (sub-proceso): un abogado se lo asigna; revisan líder jurídico y líder del proyecto; versión firmada. Siempre que hay requerimiento, el usuario debe volver a presentar planos.
4. **Subsanación**: radicado de los planos ajustados (no es un acto administrativo).
5. **Concepto de la subsanación**: mismo flujo del paso 2. Se asume que cumple.
6. **Acto que aprueba las memorias**: un abogado se lo asigna; revisan líder jurídico y líder del proyecto. Se cita y notifica.

---

### ETAPA 6 · Recibo a satisfacción de obras (`recibo_satisfaccion_obras`)

**Condición de creación:** decisión OTORGADA (siempre se hace). Si `requiere_memorias = true`, además las memorias deben estar aprobadas.

**Flujo:**
1. **Informe del usuario**: radicado de que construyó la obra o instaló el medidor o llave (radicado + PDF).
2. **Concepto técnico con visita**: el abogado selecciona el técnico. El **técnico decide la fecha de visita** y la diligencia con su concepto. Lo revisa solo la líder técnica. Registra **Cumple / No cumple**.
3. Si **No cumple** → requerimiento (un abogado se lo asigna) → **nuevo informe del usuario** → **segundo concepto con visita**.
4. **Acto que aprueba la obra** (o exige corregirla o demolerla). Un abogado se lo asigna. Se notifica.

`TODO(negocio)`: quién revisa el acto que aprueba la obra.

---

### Transversal · Tercero interviniente (`expediente_involucrado`, `tipo_vinculo = TERCERO_INTERVINIENTE`)

- Persona que **se opone** al permiso. Pasa más o menos en 1 de cada 10 casos.
- Casi siempre aparece durante el auto admite, la fijación del aviso o la visita.
- Se vincula como involucrado (app-involved) con el estado de tercero interviniente.
- Se le expide un acto que lo reconoce (`tipo_acto = RECONOCE_TERCERO`, `acto_admin_id` nullable hasta que se expida).
- El acto que lo reconoce **solo se comunica, no se notifica** (aclaración del área, 14/10/2026). Regla general: **solo se comunican** el auto que admite y el acto que reconoce al tercero, y ninguno de los dos se notifica; **todos los demás actos solo se notifican** y no llevan comunicación.
- Recibe las actuaciones siguientes igual que los solicitantes: se le **notifica** en los actos que se notifican (requerimiento, decisión, recurso…) con la tabla `notificacion`, y en los que solo se comunican (auto admite) la comunicación pública ya lo cubre, porque llega a todos sin distinguir (aclaración del área, 13/10/2026).
- `TODO(negocio)`: validar con las líderes. No se mencionó si su solicitud llega con radicado y documento.

---

## 5. Flujo de revisión de documentos (en esta app)

El cargue, las versiones y las revisiones se manejan en este microservicio, replicando el modelo y la lógica de **infraction-app**. app-docs solo almacena cada archivo.

Estados: **cargado → en revisión → devuelto / aprobado → aprobado para firma → versión final (firmada)**.

| Documento | Sube (encargado) | Revisión en el sistema (en orden) | Firma (fuera del sistema) |
|---|---|---|---|
| Auto admite, requerimiento, acto que aprueba memorias | Abogado asignado | Líder jurídico → líder del proyecto (aprobado para firma) | Subdirectora (física) |
| Decisión, acto del recurso | Abogado asignado | Líder jurídico → líder del proyecto **y** asesora de subdirección | Subdirectora (física) |
| Concepto técnico etapa 2 | Técnico seleccionado | Líder técnico (`recurso_lider_tecnico`) y SIG (`recurso_sig`), en cualquier orden → líder del proyecto | — |
| Concepto adicional (etapa 3) | Técnico seleccionado | Líder técnico | — |
| Conceptos de memorias y de obras | Técnico seleccionado | Solo líder técnica | Líder técnica |

**Reglas de revisión:**
1. Si el revisor **devuelve**, el encargado sube una nueva versión con las correcciones.
2. El revisor **no revisa dos veces**: después de devolver, se asume que se corrigió y pasa al siguiente revisor.
3. El líder del proyecto marca **"aprobado para firma"**. La siguiente versión que se suba es la firmada y queda aprobada automáticamente.
4. La subdirectora no interviene en el sistema.
5. Los documentos pendientes de subir o revisar aparecen en **Mis informes** de cada persona.

---

## 6. Validaciones de la aplicación

> `recurso_super_gestion` omite todas estas validaciones (§2.1).

| # | Validación |
|---|---|
| V1 | Solo usuarios con `recurso_gestionar` pueden crear, editar o proyectar. `recurso_consultar` es solo lectura. |
| V2 | Solo el `encargado_acto_id` de un proceso puede gestionarlo. Un proceso con encargado no puede ser tomado por otro. |
| V3 | Solo el técnico seleccionado puede cargar su concepto. El técnico debe tener `recurso_tecnico`. |
| V4 | No se crea ninguna etapa sin `acto_admite`. |
| V5 | `concepto_tecnico` de la etapa 2 solo si el auto registró fecha de visita y técnico. |
| V6 | `requerimiento` de la etapa 3 solo si existe el concepto de la etapa 2. |
| V7 | `decision` solo si existe la constancia de fijación de la Alcaldía. |
| V8 | `requiere_memorias = true` solo si `decision = OTORGADA`. |
| V9 | `memorias_calculo` solo si `requiere_memorias = true`. |
| V10 | `recibo_satisfaccion_obras` solo si `decision = OTORGADA`; si `requiere_memorias`, además memorias aprobadas. |
| V11 | Requerimientos de memorias y de obras solo si el concepto dice `cumple = false`. |
| V12 | Actos de aprobación de memorias y de obras solo si el último concepto dice `cumple = true`. |
| V13 | `recurso_reposicion` solo si la decisión está notificada. |
| V14 | Involucrado con tipo de documento NIT exige `representante_id`. |
| V15 | Un mismo concepto o requerimiento no puede quedar referenciado por dos padres a la vez. |
| V16 | Una etapa directa existe una sola vez por expediente (lo garantiza el `unique` de `expediente_id`). |

---

## 7. Concurrencia

**Problema:** varios usuarios con `recurso_gestionar` pueden trabajar sobre el mismo expediente al mismo tiempo: pisar cambios, crear dos veces la misma etapa o asignarse el mismo proceso.

| Caso | Mecanismo |
|---|---|
| Dos personas se asignan el mismo proceso | Asignación atómica: `UPDATE ... WHERE encargado_acto_id IS NULL`. 0 filas → **409**. |
| Dos personas editan el mismo registro (información base, involucrados, fuentes) | **Bloqueo optimista**: columna `version integer [not null, default: 1]` en `expediente` y tablas editables. `UPDATE ... WHERE id = :id AND version = :version`; 0 filas → **409** "Fue modificado por otra persona, recarga". |
| Dos personas crean la misma etapa | Los `unique` sobre `expediente_id` lo impiden. Capturar el error de integridad → **409**. |
| Transiciones críticas (crear etapa siguiente, cargar versión final, numerar, registrar decisión) | **Bloqueo pesimista** en transacción: `SELECT ... FROM expediente WHERE id = :id FOR UPDATE`, validar §6 y escribir. |
| Números de acto duplicados | Índice `acto_administrativo (tipo_acto, numerado)`. `TODO(negocio)`: si la numeración se reinicia cada año, incluir el año y volverlo `unique`. |

**Criterio de aceptación:** dos peticiones concurrentes sobre el mismo proceso terminan con una respuesta exitosa y una **409**, sin pérdida de datos, etapas duplicadas ni doble asignación.

---

## 8. Fases de implementación

| Fase | Entregable | Criterio de aceptación |
|---|---|---|
| 1 | Modelo y migraciones desde `concesiones_dbml.txt` + columna `version` + seed (§3.1) | Migraciones limpias; constraints, índices y catálogos cargados. |
| 2 | Permisos (§2) y protección de endpoints | Cada endpoint exige su permiso; consultar es solo lectura. |
| 3 | Clientes de app-users, app-involved y app-docs + módulo de documentos (cargue, versiones y revisiones) replicado de infraction-app | Funcionarios e involucrados se resuelven por id; los archivos se almacenan en app-docs y el flujo de revisión corre en esta app. |
| 4 | Pestaña Gestionar: información base, vincular/desvincular involucrados, representante (V14), fuentes y usos | Campos de §3 validados; expediente único. |
| 5 | Asignación "Asignarme para diligenciar" y selección de técnico | V2, V3; asignación atómica. |
| 6 | Etapa 1 + comunicación + tercero interviniente | Flujo §4-Etapa 1; V4. |
| 7 | Etapas 2 y 3 (con concepto adicional) | V5, V6. |
| 8 | Etapa 4: decisión, citación/notificación, recurso | V7, V8, V13; ejecutoria. |
| 9 | Etapas 5 y 6 | V9–V12. |
| 10 | Pestaña Mis informes (documentos por subir y por revisar) | Cada persona ve solo lo que le corresponde según encargo o permiso de revisor. |
| 11 | Pestaña Consulta + descarga del expediente completo | Un expediente se consulta y descarga completo sin ir al archivo físico. |
| 12 | Super gestión: formularios de cargue histórico | Se puede cargar cualquier etapa con documentos finales sin revisión ni asignación. |
| 13 | Concurrencia transversal (§7) | Tests concurrentes en verde. |

---

## 9. Pendientes de negocio (no implementar hasta resolver)

| Tema | Estado |
|---|---|
| Agrupación de usos para migrar datos viejos | Validar con el área (§3.1). |
| Numeración de actos por año | Confirmar. |
| Quién revisa el acto que aprueba obras | Confirmar. |
| Datos de la solicitud del tercero interviniente | Confirmar con las líderes. |
| POEA | Omitido; lo corregirá el área. |
| Prórroga, modificación y cancelación | Se verán al final (mismo expediente). |
| Plazos y alertas por etapa | Más adelante. |
| Estado del permiso | Otorgado/negado/desistido sale de `decision`; vigente = ejecutoria + 10 años; cancelado depende de la cancelación. |
