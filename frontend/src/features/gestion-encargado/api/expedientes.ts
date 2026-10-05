import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@shared/lib/api";
import type { ExpedientesEncargadoFiltros, RespuestaExpedientes } from "../types";
import { gestionEncargadoKeys } from "./queryKeys";

/** Página de expedientes con su encargado + usuarios asignables. */
export function useExpedientesEncargadoQuery(
  endpoint: string,
  filtros: ExpedientesEncargadoFiltros,
) {
  return useQuery({
    queryKey: gestionEncargadoKeys.lista(endpoint, filtros),
    queryFn: () => {
      const params = new URLSearchParams();
      params.append("page", String(filtros.page));
      params.append("limit", String(filtros.limit));
      if (filtros.radicado.trim()) params.append("radicado", filtros.radicado.trim());
      if (filtros.nombreExpediente.trim())
        params.append("nombre_expediente", filtros.nombreExpediente.trim());
      if (filtros.fechaCreacion.trim())
        params.append("fecha_creacion", filtros.fechaCreacion.trim());
      return apiRequest<RespuestaExpedientes>(`${endpoint}?${params.toString()}`);
    },
    placeholderData: keepPreviousData,
  });
}

export type BulkUpdateEncargadoInput = {
  expedienteIds: number[];
  encargadoId: number;
};

/** Reasigna el encargado de varios expedientes y refresca el listado. */
export function useBulkUpdateEncargadoMutation(bulkUpdateEndpoint: string, listaEndpoint: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ expedienteIds, encargadoId }: BulkUpdateEncargadoInput) =>
      apiRequest<{ msg?: string }>(bulkUpdateEndpoint, {
        method: "PATCH",
        body: JSON.stringify({ expediente_id: expedienteIds, encargado_id: encargadoId }),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: gestionEncargadoKeys.listas(listaEndpoint) }),
  });
}
