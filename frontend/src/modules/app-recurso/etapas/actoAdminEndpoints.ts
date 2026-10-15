import type { ActoAdminEndpoints } from "@features/acto-administrativo";
import { RECURSO_ENDPOINTS } from "@shared/lib/api";

/**
 * Adapter de endpoints de app-recurso (/recurso/actos, API.md B.3) para la
 * feature `ActoAdmin`. Lo usarán las etapas con acto administrativo (F2).
 *
 * `actoAdmin.create` no existe en el backend: el acto lo crea la etapa al
 * "Cargar versión final" (sección C). Desde `ActoAdmin` solo se corrige
 * (update), se comunica y se notifica.
 */
export const RECURSO_ACTO_ENDPOINTS: ActoAdminEndpoints = {
  actoAdmin: {
    create: RECURSO_ENDPOINTS.RECURSO_ACTO_ADMIN,
    update: RECURSO_ENDPOINTS.RECURSO_ACTO_ADMIN_UPDATE,
    delete: RECURSO_ENDPOINTS.RECURSO_ACTO_ADMIN_DELETE,
  },
  notificacion: {
    base: RECURSO_ENDPOINTS.RECURSO_NOTIFICACION,
    delete: RECURSO_ENDPOINTS.RECURSO_NOTIFICACION_DELETE,
  },
  comunicacion: {
    create: RECURSO_ENDPOINTS.RECURSO_COMUNICACION,
    update: RECURSO_ENDPOINTS.RECURSO_COMUNICACION_UPDATE,
    delete: RECURSO_ENDPOINTS.RECURSO_COMUNICACION_DELETE,
  },
};

/** Actos sin comunicación (p. ej. decisión, recurso): solo notificación. */
export const RECURSO_ACTO_ENDPOINTS_SOLO_NOTIFICACION: ActoAdminEndpoints = {
  actoAdmin: RECURSO_ACTO_ENDPOINTS.actoAdmin,
  notificacion: RECURSO_ACTO_ENDPOINTS.notificacion,
};
