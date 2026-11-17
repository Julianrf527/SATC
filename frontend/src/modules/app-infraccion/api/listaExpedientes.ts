import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, INFRACTION_ENDPOINTS } from "@shared/lib/api";
import type { Expediente } from "../types";
import { infraccionKeys } from "./queryKeys";

async function listar(endpoint: string): Promise<Expediente[]> {
  return (await apiRequest<{ data?: Expediente[] | null }>(endpoint)).data ?? [];
}

/** Expedientes a cargo del usuario (vista de gestión). */
export function useExpedientesEncargadoQuery(userId: number | undefined) {
  return useQuery({
    queryKey: infraccionKeys.expedientesEncargado(userId ?? 0),
    queryFn: () => listar(INFRACTION_ENDPOINTS.INFRACTION_BY_USER(userId as number)),
    enabled: !!userId,
    // Siempre fresco al montar: una notificación puede traer un expediente
    // recién asignado que aún no está en la caché.
    staleTime: 0,
  });
}

/** Todos los expedientes (vista de consulta). Requiere sesión. */
export function useTodosExpedientesQuery(enabled: boolean) {
  return useQuery({
    queryKey: infraccionKeys.todosExpedientes(),
    queryFn: () => listar(INFRACTION_ENDPOINTS.INFRACTION_VIEW),
    enabled,
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
    () => queryClient.invalidateQueries({ queryKey: infraccionKeys.listaExpedientes() }),
    [queryClient],
  );
}
