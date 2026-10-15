import { useCallback } from "react";
import { useQueryClient, type QueryClient } from "@tanstack/react-query";
import { recursoKeys } from "./queryKeys";

/**
 * Tras crear, cambiar o borrar algo de un expediente (información base,
 * involucrados, etapas, actos...) se invalida todo su subárbol y los
 * listados (la tarjeta lateral muestra datos de la información base).
 */
export function invalidarExpediente(queryClient: QueryClient, expedienteId: number) {
  return Promise.all([
    queryClient.invalidateQueries({ queryKey: recursoKeys.expediente(expedienteId) }),
    queryClient.invalidateQueries({ queryKey: recursoKeys.listaExpedientes() }),
  ]);
}

/** Igual que `invalidarExpediente`, para callbacks de componentes (ActoAdmin, etapas...). */
export function useInvalidarExpediente(expedienteId: number) {
  const queryClient = useQueryClient();
  return useCallback(() => invalidarExpediente(queryClient, expedienteId), [queryClient, expedienteId]);
}
