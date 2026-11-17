import type { FiltrosDocumentos } from "../types";

// Claves de react-query del módulo app-documentos. Jerárquicas: invalidar
// `documentosKeys.listas()` refresca todas las páginas/filtros y las stats.
export const documentosKeys = {
  all: ["app-documentos"] as const,
  listas: () => [...documentosKeys.all, "lista"] as const,
  lista: (filtros: FiltrosDocumentos, page: number) =>
    [...documentosKeys.listas(), filtros, page] as const,
  stats: () => [...documentosKeys.listas(), "stats"] as const,
  revisores: () => [...documentosKeys.all, "revisores"] as const,
  detalle: (id: number) => [...documentosKeys.all, "detalle", id] as const,
};
