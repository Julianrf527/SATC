import { useMutation, useQuery } from "@tanstack/react-query";
import { apiRequest, SANCTIONING_ENDPOINTS as EP } from "@shared/lib/api";
import type { ExpedienteFullResponse } from "../types";
import { sancionatorioKeys } from "./queryKeys";

/**
 * Datos completos del expediente (dirección, vereda, recursos, involucrados,
 * etapas existentes, tipo de notificación). Se vuelve a pedir cada vez que se
 * selecciona el expediente (`gcTime: 0`), como hacía el useEffect original.
 */
export function useExpedienteFullQuery(expedienteId: number | undefined) {
  return useQuery({
    queryKey: sancionatorioKeys.expedienteFull(expedienteId ?? 0),
    queryFn: () => apiRequest<ExpedienteFullResponse>(EP.FILE_FUll(expedienteId ?? 0)),
    enabled: !!expedienteId,
    staleTime: 0,
    gcTime: 0,
    retry: false,
  });
}

export type DatosBasicosPayload = {
  radicado: string;
  expediente: string;
  recurso: number[];
  motivo: string;
  vereda: number;
  direccion: string;
};

/** Actualiza los datos básicos del expediente (PUT /basic-data). */
export function useActualizarDatosBasicosMutation(expedienteId: number) {
  return useMutation({
    mutationFn: (payload: DatosBasicosPayload) =>
      apiRequest(EP.FILE_BASIC_DATA(expedienteId), {
        method: "PUT",
        body: JSON.stringify(payload),
      }),
  });
}
