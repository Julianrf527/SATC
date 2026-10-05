import { useMutation } from "@tanstack/react-query";
import { apiRequest, API_CONFIG } from "@shared/lib/api";

/**
 * Las notificaciones llegan por SSE (ver `layout/header/useNotificationStream`),
 * no hay query que invalidar: el componente quita la notificación de la lista
 * local en el `onSuccess` del `mutate`.
 */
export function useDeleteNotificationMutation() {
  return useMutation({
    mutationFn: (id: number) =>
      apiRequest(API_CONFIG.ENDPOINTS.NOTIFICATION_DELETE(id), { method: "DELETE" }),
  });
}

export function useClearNotificationsMutation() {
  return useMutation({
    mutationFn: () =>
      apiRequest(API_CONFIG.ENDPOINTS.NOTIFICATION_DELETE_ALL, { method: "DELETE" }),
  });
}
