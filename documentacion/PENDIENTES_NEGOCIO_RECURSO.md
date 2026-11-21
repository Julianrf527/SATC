# Pendientes de negocio — Concesiones de Aguas (app-recurso)

Preguntas que el plan no resuelve. Mientras no se definan, el sistema aplica
el comportamiento de la columna **Hoy**. Al resolver una, se ajusta el código
(si hace falta) y se pasa a la sección de resueltas.

## Abiertas

| # | Tema | Pregunta | Hoy |
|---|---|---|---|
| 1 | Revisión | ¿Hay tope de devoluciones o reasignación del encargado? | Sin tope y sin reasignación (`services/revision_documentos.py`, `MAX_DEVOLUCIONES`). |
| 2 | Actos | ¿La numeración de los actos se reinicia cada año? ¿Un documento puede servir para dos actos? | Solo choca el mismo numerado con la misma fecha y clase (Auto / Resolución) (`services/actos.py`, `validar_numerado_disponible`). |
| 3 | Decisión | ¿La fecha de ejecutoria se calcula sola (10 días hábiles tras notificar si no hay recurso)? | La diligencia el abogado (`PUT /etapas/{id}/decision/ejecutoria`). |
| 4 | Revisión | ¿Quién revisa el acto que reconoce al tercero interviniente? | Líder jurídico → líder del proyecto. |
| 5 | Revisión | ¿Quién revisa el acto que aprueba las obras? | Líder jurídico → líder del proyecto. |
| 6 | Expediente | ¿El número de expediente tiene formato fijo (p. ej. «CA 001-26»)? | No se valida el formato (máx. 9 caracteres). |
| 7 | Tercero | ¿La solicitud del tercero llega con radicado y documento? | Solo se vincula la persona. |
| 8 | Tercero | ¿Puede vincularse un tercero antes del auto que admite? | Sí, no se exige (V4 no aplica). |
| 9 | Tercero | ¿Al tercero solo se le notifican las actuaciones posteriores a su vinculación? | Se le notifican todas (`involucrados_notificables`). |
| 10 | Concepto | ¿Bastan los 4 datos de caudal (fuente, disponible, otorgado, usuarios)? | Solo esos 4 (`services/etapas.py`, `CAUDALES`). |
| 11 | Concepto | ¿El concepto adicional vuelve a registrar caudales? | Son opcionales. |
| 12 | Memorias | Si el concepto de la subsanación tampoco cumple, ¿hay otro ciclo? | No: el modelo admite una sola subsanación. |
| 13 | Obras | ¿El acto de obras puede «exigir corregir o demoler» aunque el concepto no cumpla? | Solo procede si el último concepto dice que cumple (V12). |

## Resueltas

| Tema | Decisión |
|---|---|
| Acto notificado (V13) | Al menos una notificación y todas exitosas (aceptada 2026-11-10). |
| Ejecutoria y calendario | Ya hay calendario de días hábiles de Colombia (lo usan las alertas). |
| Eliminar un acto | Solo super gestión; el encargado lo corrige con editar. |
| Fuentes y usos al crear el expediente | Se exige al menos una fuente y un uso. |
| Quién registra los radicados del usuario (planos, subsanación, informes) | Cualquier usuario con `recurso_gestionar`. |
| Desvincular a una persona con notificaciones | Se avisa que tiene notificaciones y, si confirma, se eliminan junto con el vínculo. Con acto que la reconoce no se puede desvincular. |
