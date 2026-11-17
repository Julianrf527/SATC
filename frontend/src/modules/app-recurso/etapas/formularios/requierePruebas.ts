// «¿Requiere práctica de pruebas?» del recurso de reposición: se responde al
// crearlo y se puede cambiar después (PUT /recurso/requiere-pruebas).

/** Primer error al crear el recurso, o `null`. */
export function validarRespuestaPruebas(requiere: boolean | null): string | null {
  return requiere === null ? "Indique si el recurso requiere práctica de pruebas" : null;
}

/** Primer error al cambiar la respuesta, o `null`. `elimina`: Sí → No con la práctica iniciada. */
export function validarRequierePruebas(actual: boolean, requiere: boolean, elimina: boolean, confirmado: boolean): string | null {
  if (actual === requiere) return "Seleccione un valor distinto al actual";
  if (elimina && !confirmado) return "Confirme que entiende que se eliminará la práctica de pruebas";
  return null;
}

/** Body del PUT (con la `version` del recurso). */
export function bodyRequierePruebas(version: number, requiere: boolean, confirmarEliminar: boolean) {
  return {
    version,
    requiere_pruebas: requiere,
    ...(confirmarEliminar ? { confirmar_eliminar_pruebas: true } : {}),
  };
}
