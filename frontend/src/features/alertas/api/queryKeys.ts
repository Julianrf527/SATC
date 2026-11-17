import type { FiltrosAlertas } from "../alertasPaginacion";

// Claves react-query de la feature alertas (indexadas por endpoint del servicio).
export const alertasKeys = {
  all: ["alertas"] as const,
  expediente: (endpoint: string) => [...alertasKeys.all, "expediente", endpoint] as const,
  todas: (endpoint: string) => [...alertasKeys.all, "todas", endpoint] as const,
  pagina: (endpoint: string, filtros: FiltrosAlertas) =>
    [...alertasKeys.todas(endpoint), "pagina", filtros] as const,
};
