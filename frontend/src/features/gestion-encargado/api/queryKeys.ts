import type { ExpedientesEncargadoFiltros } from "../types";

// Claves react-query de la feature gestion-encargado (por endpoint del servicio).
export const gestionEncargadoKeys = {
  all: ["gestion-encargado"] as const,
  listas: (endpoint: string) => [...gestionEncargadoKeys.all, "lista", endpoint] as const,
  lista: (endpoint: string, filtros: ExpedientesEncargadoFiltros) =>
    [...gestionEncargadoKeys.listas(endpoint), filtros] as const,
};
