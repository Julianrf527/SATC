import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiCall, apiRequest, API_CONFIG } from "@shared/lib/api";
import type { User } from "@shared/context/AuthContext";
import { appKeys } from "./queryKeys";

/**
 * Usuario autenticado (`/auth/me`). Devuelve `null` si no hay sesión válida
 * (cualquier respuesta no-ok o error de red), igual que el antiguo
 * `verifyToken` de MainLayout: nunca queda en estado de error.
 *
 * - `gcTime: 0`: al desmontar el layout privado (ir a /login) se descarta;
 *   al volver a montarlo se verifica de nuevo y se ve la barra de carga en vez
 *   de un `null` cacheado que rebotaría otra vez al login.
 * - `retry: false`: sin sesión no tiene sentido reintentar (y un 5xx debe
 *   llevar al login igual que antes, no dejar la barra de carga girando).
 */
export function useMeQuery() {
  return useQuery({
    queryKey: appKeys.me(),
    queryFn: async (): Promise<User | null> => {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.AUTH_ME, { method: "GET" });
        return res.ok ? (res.usuario as User) : null;
      } catch {
        return null;
      }
    },
    gcTime: 0,
    retry: false,
  });
}

/** Reemplaza el usuario en caché (lo expone `AuthContext.setUser`). */
export function useSetMe() {
  const queryClient = useQueryClient();
  return useCallback(
    (user: User | null) => queryClient.setQueryData(appKeys.me(), user),
    [queryClient],
  );
}

/**
 * Cierra sesión. Sea cual sea el resultado se recarga en `/login` (recarga
 * completa: limpia también la caché de react-query).
 */
export function useLogoutMutation() {
  return useMutation({
    mutationFn: () => apiRequest(API_CONFIG.ENDPOINTS.AUTH_LOGOUT, { method: "POST" }),
    onSettled: () => {
      window.location.href = "/login";
    },
  });
}
