import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiCall, apiRequest, INVOLVED_ENDPOINTS } from "@shared/lib/api";
import type { Involved, InvolvedFiltros, InvolvedListResponse, InvolvedSaveData } from "../types";
import { involvedKeys } from "./queryKeys";

/** Listado paginado y filtrado de involucrados. */
export function useInvolvedListQuery(filtros: InvolvedFiltros) {
  return useQuery({
    queryKey: involvedKeys.list(filtros),
    queryFn: () => {
      const params = new URLSearchParams();
      params.append("page", String(filtros.page));
      params.append("limit", String(filtros.limit));
      if (filtros.numeroDocumento.trim())
        params.append("numero_documento", filtros.numeroDocumento.trim());
      if (filtros.tipoDocumento) params.append("tipo_documento", filtros.tipoDocumento);
      if (filtros.nombre.trim()) params.append("nombre", filtros.nombre.trim());
      if (filtros.correo.trim()) params.append("correo", filtros.correo.trim());
      return apiRequest<InvolvedListResponse>(
        `${INVOLVED_ENDPOINTS.INVOLVED_MANAGE}?${params.toString()}`,
      );
    },
    placeholderData: keepPreviousData,
  });
}

/** Actualiza un involucrado e invalida los listados. */
export function useUpdateInvolvedMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: InvolvedSaveData }) =>
      apiRequest(INVOLVED_ENDPOINTS.INVOLVED_UPDATE(id), {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: involvedKeys.lists() }),
  });
}

/**
 * Busca un involucrado por documento (verificación de unicidad al editar).
 * `null` si no existe (el servicio responde 404).
 */
export async function buscarInvolvedPorDocumento(
  tipo: string,
  numero: string,
  dv?: string,
): Promise<Involved | null> {
  const res = await apiCall(INVOLVED_ENDPOINTS.INVOLVED_SEARCH(tipo, numero, dv));
  return res.ok && res.data ? (res.data as Involved) : null;
}
