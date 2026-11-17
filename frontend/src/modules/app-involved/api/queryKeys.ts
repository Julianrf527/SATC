import type { InvolvedFiltros } from "../types";

// Claves react-query del módulo app-involved.
export const involvedKeys = {
  all: ["app-involved"] as const,
  lists: () => [...involvedKeys.all, "list"] as const,
  list: (filtros: InvolvedFiltros) => [...involvedKeys.lists(), filtros] as const,
};
