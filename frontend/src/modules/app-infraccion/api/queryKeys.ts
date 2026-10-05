// Claves de react-query del módulo app-infraccion. Jerárquicas:
//  - `infraccionKeys.expediente(id)` invalida todo lo de un expediente
//    (detalle, involucrados y las etapas).
//  - `infraccionKeys.catalogos()` agrupa listas fijas (tipos de medida, de notificación,
//    municipios, recursos, tipos de afectación, quejosos).
//  - `infraccionKeys.listaExpedientes()` agrupa los listados de las vistas de
//    gestión (por encargado) y consulta (todos).
export const infraccionKeys = {
  all: ["app-infraccion"] as const,

  expediente: (expedienteId: number) =>
    [...infraccionKeys.all, "expediente", expedienteId] as const,
  completo: (expedienteId: number) =>
    [...infraccionKeys.expediente(expedienteId), "completo"] as const,
  involucrados: (expedienteId: number) =>
    [...infraccionKeys.expediente(expedienteId), "involucrados"] as const,
  respuesta: (expedienteId: number) =>
    [...infraccionKeys.expediente(expedienteId), "etapa", "respuesta"] as const,
  concepto: (expedienteId: number) =>
    [...infraccionKeys.expediente(expedienteId), "etapa", "concepto"] as const,
  cierre: (expedienteId: number) =>
    [...infraccionKeys.expediente(expedienteId), "etapa", "cierre"] as const,

  catalogos: () => [...infraccionKeys.all, "catalogos"] as const,
  tiposNotificacion: () => [...infraccionKeys.catalogos(), "tipos-notificacion"] as const,
  tiposMedida: () => [...infraccionKeys.catalogos(), "tipos-medida"] as const,
  municipios: () => [...infraccionKeys.catalogos(), "municipios"] as const,
  recursosAfectados: () => [...infraccionKeys.catalogos(), "recursos-afectados"] as const,
  tiposAfectacion: () => [...infraccionKeys.catalogos(), "tipos-afectacion"] as const,
  quejosos: () => [...infraccionKeys.catalogos(), "quejosos"] as const,

  listaExpedientes: () => [...infraccionKeys.all, "lista-expedientes"] as const,
  expedientesEncargado: (userId: number) =>
    [...infraccionKeys.listaExpedientes(), "encargado", userId] as const,
  todosExpedientes: () => [...infraccionKeys.listaExpedientes(), "todos"] as const,
};
