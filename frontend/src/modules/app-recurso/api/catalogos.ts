import { useQuery } from "@tanstack/react-query";
import { apiRequest, RECURSO_ENDPOINTS } from "@shared/lib/api";
import { useErrorToast } from "@shared/hooks/useErrorToast";
import type { CatalogosRecurso, SetToast } from "../types";
import { recursoKeys } from "./queryKeys";

/** Catálogos casi fijos: se reutilizan 5 min entre pantallas. */
const STALE_CATALOGO = 5 * 60_000;

const VACIO: CatalogosRecurso = {
  municipios: [],
  tipos_fuente: [],
  fuentes: [],
  usos: [],
  tipos_notificacion: [],
};

/** Todos los catálogos del formulario en una sola petición (GET /recurso/catalogos). */
export function useCatalogosQuery() {
  return useQuery({
    queryKey: recursoKeys.catalogos(),
    queryFn: async () =>
      (await apiRequest<{ data?: Partial<CatalogosRecurso> }>(RECURSO_ENDPOINTS.RECURSO_CATALOGOS)).data ?? {},
    staleTime: STALE_CATALOGO,
    select: (data): CatalogosRecurso => ({ ...VACIO, ...data }),
  });
}

/** Catálogos + toast si fallan (pantallas de Gestionar y Consulta). */
export function useCatalogosRecurso(setToast: SetToast) {
  const query = useCatalogosQuery();
  useErrorToast(query.error, setToast, "Error al cargar los catálogos");
  return { catalogos: query.data ?? VACIO, cargando: query.isPending };
}
