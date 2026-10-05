import { useQuery } from "@tanstack/react-query";
import { apiRequest, API_CONFIG } from "@shared/lib/api";
import { auditoriaKeys } from "./queryKeys";

/** Elemento de catálogo tal como lo devuelven los servicios (nombre o name). */
export type CatalogoItem = {
  id: number;
  nombre?: string;
  name?: string;
  veredas?: CatalogoItem[] | null;
};

// Los catálogos casi no cambian: se cachean 5 min entre aperturas del modal.
const CATALOGO_STALE_TIME = 5 * 60 * 1000;

/**
 * Catálogo genérico (GET que devuelve `{ data: [...] }`). Si la petición
 * falla devuelve lista vacía: el detalle degrada a mostrar los IDs crudos.
 */
export function useCatalogoQuery(url: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: auditoriaKeys.catalogo(url ?? ""),
    queryFn: async () => {
      try {
        const res = await apiRequest<{ data?: CatalogoItem[] }>(url!);
        return res.data ?? [];
      } catch {
        return [] as CatalogoItem[];
      }
    },
    enabled: enabled && !!url,
    staleTime: CATALOGO_STALE_TIME,
  });
}

/** Nombres de etapas por ID (enriquecimiento opcional; silencioso si falla). */
export function useEtapasNombresQuery(ids: number[], enabled: boolean) {
  return useQuery({
    queryKey: auditoriaKeys.etapas(ids),
    queryFn: async () => {
      try {
        const res = await apiRequest<{ data?: Record<number, string> }>(
          API_CONFIG.ENDPOINTS.AUDIT_ETAPAS_BATCH,
          { method: "POST", body: JSON.stringify(ids) },
        );
        return res.data ?? {};
      } catch {
        return {} as Record<number, string>;
      }
    },
    enabled: enabled && ids.length > 0,
    staleTime: CATALOGO_STALE_TIME,
  });
}
