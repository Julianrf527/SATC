/**
 * API pública del cliente HTTP. Importar siempre desde `@shared/lib/api`.
 *
 * `API_CONFIG.ENDPOINTS` se mantiene por compatibilidad (mapa plano con todos
 * los servicios). Código nuevo puede importar el mapa del servicio concreto
 * (`USERS_ENDPOINTS`, `INFRACTION_ENDPOINTS`, ...).
 */
import { USERS_ENDPOINTS } from "./endpoints/users";
import { SANCTIONING_ENDPOINTS } from "./endpoints/sanctioning";
import { DOCUMENTS_ENDPOINTS } from "./endpoints/documents";
import { INVOLVED_ENDPOINTS } from "./endpoints/involved";
import { INFRACTION_ENDPOINTS } from "./endpoints/infraction";

export {
  BASE_URL,
  apiCall,
  apiRequest,
  ApiError,
  jsonBody,
  getErrorMessage,
  formatApiErrorDetail,
} from "./client";

export {
  USERS_ENDPOINTS,
  SANCTIONING_ENDPOINTS,
  DOCUMENTS_ENDPOINTS,
  INVOLVED_ENDPOINTS,
  INFRACTION_ENDPOINTS,
};

export const API_CONFIG = {
  ENDPOINTS: {
    ...USERS_ENDPOINTS,
    ...SANCTIONING_ENDPOINTS,
    ...DOCUMENTS_ENDPOINTS,
    ...INVOLVED_ENDPOINTS,
    ...INFRACTION_ENDPOINTS,
  },
};
