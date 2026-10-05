import { useMutation, useQuery } from "@tanstack/react-query";
import type { ExpedienteBase, ExpedientesAdapter, FiltroAvanzadoBase } from "./types";

/**
 * Hooks de datos de la lista de expedientes. Reciben el adapter del módulo,
 * así que las claves cuelgan de `adapter.queryKey` (namespace del módulo).
 */

/** Veredas de un municipio (modal de filtros avanzados). */
export function useVeredasMunicipioQuery<T extends ExpedienteBase, F extends FiltroAvanzadoBase>(
  adapter: ExpedientesAdapter<T, F>,
  municipioId: number | undefined,
) {
  return useQuery({
    queryKey: [...adapter.queryKey, "veredas", municipioId],
    queryFn: () => adapter.obtenerVeredas(municipioId as number),
    enabled: !!municipioId,
  });
}

/**
 * Búsqueda avanzada en BD. Es una mutación (POST disparado por el usuario);
 * el componente guarda el resultado y muestra el toast en su `onSuccess`.
 */
export function useFiltroAvanzadoMutation<T extends ExpedienteBase, F extends FiltroAvanzadoBase>(
  adapter: ExpedientesAdapter<T, F>,
) {
  return useMutation({
    mutationKey: [...adapter.queryKey, "filtro-avanzado"],
    mutationFn: (filtros: F) => adapter.filtrarAvanzado(filtros),
  });
}
