import type { ActoAdminEndpoints } from "@features/acto-administrativo";
import { INFRACTION_ENDPOINTS } from "@shared/lib/api";

/**
 * Adapter de endpoints de app-infraction para la feature `ActoAdmin`
 * (medida preventiva, auto de requerimiento y cierre). Antes había una copia
 * por componente.
 */
export const INFRACCION_ACTO_ENDPOINTS: ActoAdminEndpoints = {
  actoAdmin: {
    create: INFRACTION_ENDPOINTS.INFRACTION_ACTO_ADMIN,
    update: INFRACTION_ENDPOINTS.INFRACTION_ACTO_ADMIN_UPDATE,
    delete: INFRACTION_ENDPOINTS.INFRACTION_ACTO_ADMIN_DELETE,
  },
  notificacion: {
    base: INFRACTION_ENDPOINTS.INFRACTION_NOTIFICACION,
    delete: INFRACTION_ENDPOINTS.INFRACTION_NOTIFICACION_DELETE,
  },
  comunicacion: {
    create: INFRACTION_ENDPOINTS.INFRACTION_COMUNICACION,
    update: INFRACTION_ENDPOINTS.INFRACTION_COMUNICACION_UPDATE,
    delete: INFRACTION_ENDPOINTS.INFRACTION_COMUNICACION_DELETE,
  },
};

/** Cierre: solo notificación (sin comunicación), igual que antes. */
export const INFRACCION_ACTO_ENDPOINTS_SOLO_NOTIFICACION: ActoAdminEndpoints = {
  actoAdmin: INFRACCION_ACTO_ENDPOINTS.actoAdmin,
  notificacion: INFRACCION_ACTO_ENDPOINTS.notificacion,
};
