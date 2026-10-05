import { useEffect, useState } from "react";
import { API_CONFIG } from "@shared/lib/api";
import type { Notification } from "./notificationTypes";

const RECONNECT_DELAY_MS = 2000;

/**
 * Suscripción SSE a las notificaciones del usuario. El servidor envía la
 * lista completa en cada mensaje (`{ notifications: [...] }`); otros mensajes
 * (heartbeat) se ignoran. Ante error se cierra y reconecta a los 2 s.
 *
 * Devuelve `null` hasta recibir el primer mensaje (el Header no pinta la
 * campana hasta entonces) y un setter para quitar notificaciones localmente
 * tras borrarlas en el servidor.
 */
export function useNotificationStream() {
  const [notifications, setNotifications] = useState<Notification[] | null>(null);

  useEffect(() => {
    let baseUrl = window.ENV?.VITE_API_URL ?? import.meta.env.VITE_API_URL ?? "";
    if (baseUrl.endsWith("/")) baseUrl = baseUrl.slice(0, -1);
    const streamUrl = `${baseUrl}${API_CONFIG.ENDPOINTS.NOTIFICATION_STREAM}`;

    let eventSource: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connect = () => {
      eventSource = new window.EventSource(streamUrl, { withCredentials: true });

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.notifications) setNotifications(data.notifications);
        } catch {
          // Puede ser heartbeat u otro mensaje
        }
      };

      eventSource.onerror = () => {
        if (eventSource) {
          eventSource.close();
          eventSource = null;
        }
        // Reintento simple para mantener el stream activo
        if (!reconnectTimer) {
          reconnectTimer = setTimeout(() => {
            reconnectTimer = null;
            connect();
          }, RECONNECT_DELAY_MS);
        }
      };
    };

    connect();

    return () => {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (eventSource) eventSource.close();
    };
  }, []);

  return [notifications, setNotifications] as const;
}
