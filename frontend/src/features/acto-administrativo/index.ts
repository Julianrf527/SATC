// API pública de la feature acto-administrativo. Fuera de esta carpeta, importar
// SOLO desde "@features/acto-administrativo" (nunca rutas internas).
export { default as ActoAdmin } from "./ActoAdmin";
export { DEFAULT_ENDPOINTS } from "./actoAdminConfig";
export type {
  ActoAdminEndpoints,
  ActoAdminStageBinding,
  TipoActo,
  SetToast,
} from "./actoAdminConfig";
