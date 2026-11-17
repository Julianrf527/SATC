import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, SANCTIONING_ENDPOINTS as EP } from "@shared/lib/api";
import type { Expediente } from "@shared/types/sancionatorio";
import { sancionatorioKeys } from "./queryKeys";

async function listar(endpoint: string): Promise<Expediente[]> {
  return (await apiRequest<{ data?: Expediente[] | null }>(endpoint)).data ?? [];
}

/** Expedientes a cargo del usuario (vista de gestión). */
export function useExpedientesEncargadoQuery(userId: number | undefined) {
  return useQuery({
    queryKey: sancionatorioKeys.expedientesEncargado(userId ?? 0),
    queryFn: () => listar(EP.FILES_BY_USER(userId as number)),
    enabled: !!userId,
    // Siempre fresco al montar: una notificación puede traer un expediente
    // recién asignado que aún no está en la caché.
    staleTime: 0,
  });
}

/** Todos los expedientes, archivados o no (vista de consulta). */
export function useTodosExpedientesQuery() {
  return useQuery({
    queryKey: sancionatorioKeys.todosExpedientes(),
    queryFn: () => listar(EP.FILES_VIEW),
    staleTime: 0,
  });
}

/**
 * Vuelve a pedir los listados (gestión y consulta) tras crear, editar o
 * archivar un expediente.
 */
export function useInvalidarListaExpedientes() {
  const queryClient = useQueryClient();
  return useCallback(
    () => queryClient.invalidateQueries({ queryKey: sancionatorioKeys.listaExpedientes() }),
    [queryClient],
  );
}
