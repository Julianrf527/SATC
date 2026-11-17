import { useCallback } from "react";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { infraccionKeys } from "./queryKeys";

/**
 * Tras crear, cambiar o borrar algo de un expediente (etapa, acto,
 * notificación, involucrado, archivado, informe, datos básicos...) se
 * invalida TODO su subárbol (`completo` incluido: última etapa y estado los
 * calcula el backend) y los listados, para que la tarjeta lateral y los
 * filtros rápidos (etapa, estado) también se actualicen.
 */
export function invalidarExpediente(queryClient: QueryClient, expedienteId: number) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: infraccionKeys.expediente(expedienteId) }),
    queryClient.invalidateQueries({ queryKey: infraccionKeys.listaExpedientes() }),
  ]);
}

/** Igual que `invalidarExpediente`, para usar en componentes (callbacks de ActoAdmin, involucrados...). */
export function useInvalidarExpediente(expedienteId: number) {
  const queryClient = useQueryClient();
  return useCallback(() => invalidarExpediente(queryClient, expedienteId), [queryClient, expedienteId]);
}
