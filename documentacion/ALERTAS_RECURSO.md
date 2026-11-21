# Alertas de Concesiones de Aguas (app-recurso)

Inventario de las alertas de vencimiento que calcula app-recurso para la pestaña
**Alertas** (`/recurso/alerts`). Fuente: `app-recurso/services/alertas.py`.

## Cómo funcionan

- **Se calculan al vuelo**: no hay tabla de alertas. Cada alerta existe solo
  mientras su hito no se cumple y desaparece en cuanto se cumple.
- **Una alerta por etapa a la vez**: primera versión → revisión → versión final.
  Al cumplirse una, nace la siguiente.
- **Proceso activo**: se mira solo el proceso de revisión vigente de la etapa.
  Las devoluciones no reinician el conteo.
- **Días**: hábiles (Colombia: sin sábados, domingos ni festivos), salvo el
  recurso de reposición, que cuenta días **calendario**. El día de inicio no
  cuenta.

### Semáforo

| Estado | Condición |
|---|---|
| Verde | menos del 50 % del plazo |
| Amarillo | desde el 50 % |
| Rojo | desde el 80 % |
| Vencido | pasado el último día del plazo |

### Quién la ve y a dónde lleva

- La pestaña se ve con `recurso_alertas` (menú, ruta y endpoint).
- **Mis alertas**: las que le corresponden al usuario. **Todas**: todas (quien
  no tiene nada a su cargo ve "Mis alertas" vacía, pero puede ver "Todas").
- **Responsable**: la alerta es del encargado de la columna "Encargado",
  salvo mientras el documento está **en revisión**: entonces es de los roles
  del paso actual que aún no han revisado (p. ej. líder técnico y SIG en el
  concepto de la etapa 2; luego el líder del proyecto). Es por rol: todos los
  usuarios con ese permiso la ven en "Mis alertas". Si el documento se
  devuelve o queda aprobado para firma, vuelve al encargado. El plazo no
  cambia. La tabla muestra "Pendiente: <roles>".
- Botón de cada alerta:
  - **Revisor de turno**: **Actuación** abre el proceso en Mis actuaciones.
  - **Técnico** (`recurso_tecnico`): si la tarea es suya y ya tiene proceso,
    **Actuación** abre ese proceso en Mis actuaciones; si no, Consulta.
  - **Gestionar** (`recurso_gestionar`): abre el expediente en Gestionar.
  - **Los demás**: abre el expediente en Consulta.
  - En todos los casos el expediente abre en la pestaña de la etapa de la alerta.

## Inventario (19 alertas)

### 1. Auto que admite

| Alerta | Plazo | Cuenta desde | Termina cuando | Encargado |
|---|---|---|---|---|
| `admite_primera_version` | 4 hábiles | la asignación del encargado (nace el proceso) | existe la versión 1 | abogado asignado |
| `admite_revision` | 3 hábiles | la versión 1 | queda aprobado para firma | abogado asignado |
| `admite_version_final` | 3 hábiles | la aprobación para firma | se carga el acto | abogado asignado |
| `admite_aviso_publicado` | 10 hábiles | el registro de la comunicación del auto | se cumplen los 10 días | abogado del acto |

`admite_aviso_publicado` es **informativa**: muestra en qué día del aviso va
(«día X de 10») y desaparece sola al cumplirse.

### 2. Concepto técnico (etapa 2)

| Alerta | Plazo | Cuenta desde | Termina cuando | Encargado |
|---|---|---|---|---|
| `concepto_primera_version` | 16 hábiles | la fecha de visita técnica | existe la versión 1 | técnico |
| `concepto_version_final` | 5 hábiles | la versión 1 | se carga la versión final | técnico |

### 3. Requerimiento (etapa 3)

Solo si el concepto de la etapa 2 **no** dice `DECIDE`.

| Alerta | Plazo | Cuenta desde | Termina cuando | Encargado |
|---|---|---|---|---|
| `requerimiento_primera_version` | 6 hábiles | la versión final del concepto de la etapa 2 | existe la versión 1 | abogado del requerimiento (vacío si nadie se lo ha asignado; la alerta corre igual) |
| `requerimiento_revision` | 4 hábiles | la versión 1 | queda aprobado para firma | abogado del requerimiento |
| `requerimiento_version_final` | 2 hábiles | la aprobación para firma | se carga el acto | abogado del requerimiento |

### 4. Concepto técnico adicional

| Alerta | Plazo | Cuenta desde | Termina cuando | Encargado |
|---|---|---|---|---|
| `concepto_adicional_tecnico` | 5 hábiles | el registro de la respuesta del usuario al requerimiento | se asigna el técnico | abogado del requerimiento |
| `concepto_adicional_primera_version` | 5 hábiles | la asignación del técnico | existe la versión 1 | técnico |
| `concepto_adicional_revision` | 2 hábiles | la versión 1 | queda aprobado para firma | técnico |
| `concepto_adicional_version_final` | 1 hábil | la aprobación para firma | se carga la versión final | técnico |

### 5. Decisión (etapa 4)

| Alerta | Plazo | Cuenta desde | Termina cuando | Encargado |
|---|---|---|---|---|
| `decision_primera_version` | 6 hábiles | la versión final del concepto adicional (o la del concepto de la etapa 2 si dice `DECIDE`) | existe la versión 1 | abogado de la decisión |
| `decision_revision` | 4 hábiles | la versión 1 | queda aprobado para firma | abogado de la decisión |
| `decision_version_final` | 2 hábiles | la aprobación para firma | se carga el acto | abogado de la decisión |

### 6. Recurso de reposición (días calendario)

Todo cuenta desde que **se registra el recurso** en el sistema (no desde la
fecha del escrito).

| Alerta | Cuándo aplica | Plazo | Cuenta desde | Termina cuando | Encargado |
|---|---|---|---|---|---|
| `recurso_acto` | sin práctica de pruebas | 60 calendario | el registro del recurso | se carga el acto que resuelve | abogado del recurso |
| `recurso_concepto_pruebas` | con práctica de pruebas | 30 calendario | el registro del recurso | se carga la versión final del concepto de pruebas | técnico del concepto; mientras no exista, el abogado del auto de pruebas |
| `recurso_acto_tras_pruebas` | con práctica de pruebas | 30 calendario | la versión final del concepto de pruebas | se carga el acto que resuelve | abogado del recurso |

Si cambia la respuesta a «¿Requiere práctica de pruebas?», se aplica la regla
nueva **sin reiniciar el conteo**: sigue contando desde el registro del recurso.

## Lo que no es una alerta de esta pestaña

- **Visita técnica dentro de los 10 días hábiles siguientes al numerado del
  auto**: es un aviso al cargar el auto que admite (`advertencia_visita`), que
  no bloquea el cargue.

## Pendiente de definir

- Requerimientos de **memorias** y de **obras**: no tienen alertas todavía.
