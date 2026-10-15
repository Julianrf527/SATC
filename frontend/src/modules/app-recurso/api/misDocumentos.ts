import { useCallback } from "react";
import { keepPreviousData, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, RECURSO_ENDPOINTS } from "@shared/lib/api";
import type { MisDocumentosResponse } from "../types";
import { construirQueryMisDocumentos, type FiltrosMisDocumentos } from "./misDocumentosParams";
import { recursoKeys } from "./queryKeys";

export { FILTROS_MIS_DOCUMENTOS, type FiltrosMisDocumentos } from "./misDocumentosParams";

export function useMisDocumentosQuery(filtros: FiltrosMisDocumentos, page: number) {
  return useQuery({
    queryKey: recursoKeys.misDocumentosLista({ ...filtros, page }),
    queryFn: () =>
      apiRequest<MisDocumentosResponse>(
        `${RECURSO_ENDPOINTS.RECURSO_MIS_DOCUMENTOS}?${construirQueryMisDocumentos(filtros, page)}`,
      ),
    placeholderData: keepPreviousData,
    // Siempre fresco: una notificación puede traer un documento recién asignado.
    staleTime: 0,
  });
}

/** Recarga Mis informes (lista y procesos abiertos) tras revisar o subir versión. */
export function useInvalidarMisDocumentos() {
  const queryClient = useQueryClient();
  return useCallback(
    () => queryClient.invalidateQueries({ queryKey: recursoKeys.misDocumentos() }),
    [queryClient],
  );
}
