import { useEffect, useRef } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { apiRequest } from "@shared/lib/api";
import type { AlertasExpedienteResponse, AlertasPaginadasResponse, SetToast } from "../types";
import { urlAlertasPaginadas, type FiltrosAlertas } from "../alertasPaginacion";
import { alertasKeys } from "./queryKeys";

/** Alertas de un expediente (endpoint inyectado por el módulo). */
export function useAlertasExpedienteQuery(endpoint: string) {
  return useQuery({
    queryKey: alertasKeys.expediente(endpoint),
    queryFn: async () =>
      (await apiRequest<AlertasExpedienteResponse>(endpoint)).alertas ?? {},
  });
}

/**
 * Una página de las alertas de todos los expedientes del servicio, con los
 * filtros resueltos en el servidor. Mientras carga otra página o filtro se
 * conserva la anterior (sin parpadeo de la tabla).
 */
export function useAlertasPaginadasQuery(endpoint: string, filtros: FiltrosAlertas) {
  return useQuery({
    queryKey: alertasKeys.pagina(endpoint, filtros),
    queryFn: () => apiRequest<AlertasPaginadasResponse>(urlAlertasPaginadas(endpoint, filtros)),
    placeholderData: keepPreviousData,
  });
}

/** Muestra un toast cuando un query de alertas falla (comportamiento previo). */
export function useErrorToast(error: Error | null, setToast: SetToast, fallback: string) {
  // Ref: un `setToast` inline del padre no debe re-disparar el toast.
  const setToastRef = useRef(setToast);
  useEffect(() => {
    setToastRef.current = setToast;
  }, [setToast]);
  useEffect(() => {
    if (!error) return;
    setToastRef.current({ id: Date.now(), message: error.message || fallback, type: "error" });
  }, [error, fallback]);
}
