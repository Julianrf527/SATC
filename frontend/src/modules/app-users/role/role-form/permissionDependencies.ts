/**
 * Dependencias obligatorias entre permisos en el editor de roles.
 *
 * Lógica pura (sin React ni API): las reglas llegan del backend en
 * `Permiso.requiere` (nombres de los permisos que exige en el mismo rol) y aquí
 * solo se calcula qué está bloqueado, qué se quita en cascada y qué incumple
 * un rol. El backend repite la validación al guardar (422).
 */

export type PermisoDependiente = {
  id: number;
  nombre: string;
  requiere?: string[];
};

type Catalogo = readonly PermisoDependiente[];

function nombresSeleccionados(seleccion: readonly number[], catalogo: Catalogo): Set<string> {
  const ids = new Set(seleccion);
  return new Set(catalogo.filter((p) => ids.has(p.id)).map((p) => p.nombre));
}

/** Nombres requeridos por `permiso` que no están en la selección. */
export function requisitosFaltantes(
  permiso: PermisoDependiente,
  seleccion: readonly number[],
  catalogo: Catalogo,
): string[] {
  const nombres = nombresSeleccionados(seleccion, catalogo);
  return (permiso.requiere ?? []).filter((r) => !nombres.has(r));
}

/** Un permiso no marcado está bloqueado mientras le falte algún requerido. */
export function estaBloqueado(
  permiso: PermisoDependiente,
  seleccion: readonly number[],
  catalogo: Catalogo,
): boolean {
  return !seleccion.includes(permiso.id) && requisitosFaltantes(permiso, seleccion, catalogo).length > 0;
}

/**
 * Marca `id` si no está bloqueado. Devuelve la misma selección si no se pudo.
 */
export function agregarPermiso(
  seleccion: readonly number[],
  id: number,
  catalogo: Catalogo,
): number[] {
  const permiso = catalogo.find((p) => p.id === id);
  if (!permiso || seleccion.includes(id)) return [...seleccion];
  if (requisitosFaltantes(permiso, seleccion, catalogo).length > 0) return [...seleccion];
  return [...seleccion, id];
}

/**
 * Desmarca `ids` y, en cascada, todo permiso marcado que dependa (directa o
 * transitivamente) de alguno de los quitados. `quitados` son solo los que se
 * fueron en cascada (no los pedidos), para avisar al usuario.
 *
 * Solo se sigue la cadena desde lo que se quita: un rol viejo que ya incumplía
 * no pierde permisos por desmarcar algo que no tiene que ver.
 */
export function quitarConDependientes(
  seleccion: readonly number[],
  ids: readonly number[],
  catalogo: Catalogo,
): { seleccion: number[]; quitados: number[] } {
  const pedidos = new Set(ids);
  const resultado = new Set(seleccion.filter((id) => !pedidos.has(id)));
  const quitados: number[] = [];
  let pendientes = catalogo.filter((p) => pedidos.has(p.id)).map((p) => p.nombre);

  while (pendientes.length > 0) {
    const removidos = new Set(pendientes);
    pendientes = [];
    for (const p of catalogo) {
      if (!resultado.has(p.id)) continue;
      if ((p.requiere ?? []).some((r) => removidos.has(r))) {
        resultado.delete(p.id);
        quitados.push(p.id);
        pendientes.push(p.nombre);
      }
    }
  }

  return { seleccion: seleccion.filter((id) => resultado.has(id)), quitados };
}

/**
 * "Todos" de una categoría. Marca los que se puedan, resolviendo el orden
 * (primero los requeridos, luego sus dependientes); los que exigen algo fuera
 * de la categoría que no esté marcado quedan sin marcar. Si ya no queda nada
 * por marcar (todos marcados, o los restantes están bloqueados), desmarca la
 * categoría completa, con cascada a dependientes de otras categorías.
 */
export function alternarCategoria(
  seleccion: readonly number[],
  idsCategoria: readonly number[],
  catalogo: Catalogo,
): { seleccion: number[]; quitados: number[] } {
  const marcados = marcarCategoria(seleccion, idsCategoria, catalogo);
  if (marcados.length !== seleccion.length) return { seleccion: marcados, quitados: [] };
  return quitarConDependientes(seleccion, idsCategoria, catalogo);
}

function marcarCategoria(
  seleccion: readonly number[],
  idsCategoria: readonly number[],
  catalogo: Catalogo,
): number[] {
  let actual = [...seleccion];
  let cambio = true;
  while (cambio) {
    cambio = false;
    for (const id of idsCategoria) {
      if (actual.includes(id)) continue;
      const siguiente = agregarPermiso(actual, id, catalogo);
      if (siguiente.length !== actual.length) {
        actual = siguiente;
        cambio = true;
      }
    }
  }
  return actual;
}

export type Incumplimiento = {
  permiso: PermisoDependiente;
  faltan: string[];
};

/** Permisos marcados a los que les falta algún requerido (rol que no se puede guardar). */
export function incumplimientos(
  seleccion: readonly number[],
  catalogo: Catalogo,
): Incumplimiento[] {
  const ids = new Set(seleccion);
  return catalogo
    .filter((p) => ids.has(p.id))
    .map((permiso) => ({ permiso, faltan: requisitosFaltantes(permiso, seleccion, catalogo) }))
    .filter((i) => i.faltan.length > 0);
}
