import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiRequest } from "@shared/lib/api";
import type { AlertasExpedienteResponse, AlertasTodasResponse, SetToast } from "../types";
import { alertasKeys } from "./queryKeys";

/** Alertas de un expediente (endpoint inyectado por el módulo). */
export function useAlertasExpedienteQuery(endpoint: string) {
  return useQuery({
    queryKey: alertasKeys.expediente(endpoint),
    queryFn: async () =>
      (await apiRequest<AlertasExpedienteResponse>(endpoint)).alertas ?? {},
  });
}

/** Alertas de todos los expedientes del servicio. */
export function useAlertasTodasQuery(endpoint: string) {
  return useQuery({
    queryKey: alertasKeys.todas(endpoint),
    queryFn: () => apiRequest<AlertasTodasResponse>(endpoint),
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
