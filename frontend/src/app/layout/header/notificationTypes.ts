export type Notification = {
  id: number;
  mensaje: string;
  id_vinculada: string;
  tipo: string;
};

type NotificationRoute = string | { pathname: string; state: object };

export type NotificationTypeConfig = {
  label: string;
  dotClass: string;
  /** Pantalla destino al pulsar "Ver detalle"; sin `route` no hay botón. */
  route?: (idVinculada: string) => NotificationRoute;
};

/**
 * Ruteo por `tipo` de notificación (lo fija el backend al crearla).
 *
 * - `documento`       → /document/manage, selecciona el documento `id_vinculada`.
 * - `expediente`      → /file/manage (sancionatorio), selecciona el radicado.
 * - `expediente_infraccion` → /infraction/manage, selecciona el radicado.
 * - `informe_tecnico` → /infraction/my-reports y abre el proceso del informe
 *                       `id_vinculada` (id del informe técnico) vía `informeIdToSelect`.
 * - cualquier otro    → "Aviso", sin navegación (solo descartar).
 */
export const NOTIFICATION_TYPES: Record<string, NotificationTypeConfig> = {
  documento: {
    label: "Documento",
    dotClass: "bg-primary",
    route: (id) => ({
      pathname: "/document/manage",
      state: { documentoIdToSelect: id, timestamp: Date.now() },
    }),
  },
  expediente: {
    label: "Expediente",
    dotClass: "bg-info",
    route: (id) => ({
      pathname: "/file/manage",
      state: { radicadoToSelect: id, timestamp: Date.now() },
    }),
  },
  expediente_infraccion: {
    label: "Expediente",
    dotClass: "bg-info",
    route: (id) => ({
      pathname: "/infraction/manage",
      state: { radicadoToSelect: id, timestamp: Date.now() },
    }),
  },
  informe_tecnico: {
    label: "Informe",
    dotClass: "bg-warning",
    route: (id) => ({
      pathname: "/infraction/my-reports",
      state: { informeIdToSelect: id, timestamp: Date.now() },
    }),
  },
};

const DEFAULT_CONFIG: NotificationTypeConfig = {
  label: "Aviso",
  dotClass: "bg-base-content/40",
};

export function getNotificationConfig(tipo: string): NotificationTypeConfig {
  return NOTIFICATION_TYPES[tipo] ?? DEFAULT_CONFIG;
}
