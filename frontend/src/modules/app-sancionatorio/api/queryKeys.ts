// Claves de react-query del módulo app-sancionatorio. Jerárquicas: invalidar
// `sancionatorioKeys.expediente(id)` refresca todo lo de ese expediente.
export const sancionatorioKeys = {
  all: ["app-sancionatorio"] as const,
  catalogos: () => [...sancionatorioKeys.all, "catalogos"] as const,
  tiposMedida: () => [...sancionatorioKeys.catalogos(), "tipos-medida"] as const,
  tiposCesacion: () => [...sancionatorioKeys.catalogos(), "tipos-cesacion"] as const,
  tiposSancion: () => [...sancionatorioKeys.catalogos(), "tipos-sancion"] as const,
  municipios: () => [...sancionatorioKeys.catalogos(), "municipios"] as const,
  recursosAfectados: () => [...sancionatorioKeys.catalogos(), "recursos-afectados"] as const,
  listaExpedientes: () => [...sancionatorioKeys.all, "lista-expedientes"] as const,
  expedientesEncargado: (userId: number) =>
    [...sancionatorioKeys.listaExpedientes(), "encargado", userId] as const,
  todosExpedientes: () => [...sancionatorioKeys.listaExpedientes(), "todos"] as const,
  expediente: (expedienteId: number) =>
    [...sancionatorioKeys.all, "expediente", expedienteId] as const,
  expedienteFull: (expedienteId: number) =>
    [...sancionatorioKeys.expediente(expedienteId), "full"] as const,
  etapa: (expedienteId: number, etapa: string) =>
    [...sancionatorioKeys.expediente(expedienteId), "etapa", etapa] as const,
  migracionMedida: (radicado: string) =>
    [...sancionatorioKeys.all, "migracion-medida", radicado] as const,
};
