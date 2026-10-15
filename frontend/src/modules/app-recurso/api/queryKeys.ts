// Claves de react-query del módulo app-recurso. Jerárquicas:
//  - `recursoKeys.expediente(id)` invalida todo lo de un expediente (detalle,
//    involucrados y etapas: el árbol de etapas llega en el detalle).
//  - `recursoKeys.listaExpedientes()` agrupa los listados paginados.
//  - `recursoKeys.misDocumentos()` agrupa Mis informes y los procesos de revisión.
export const recursoKeys = {
  all: ["app-recurso"] as const,

  catalogos: () => [...recursoKeys.all, "catalogos"] as const,

  listaExpedientes: () => [...recursoKeys.all, "lista-expedientes"] as const,
  lista: (filtros: Record<string, unknown>) => [...recursoKeys.listaExpedientes(), filtros] as const,

  expediente: (expedienteId: number) => [...recursoKeys.all, "expediente", expedienteId] as const,
  detalle: (expedienteId: number) => [...recursoKeys.expediente(expedienteId), "detalle"] as const,
  documentos: (expedienteId: number) => [...recursoKeys.expediente(expedienteId), "documentos"] as const,

  misDocumentos: () => [...recursoKeys.all, "mis-documentos"] as const,
  misDocumentosLista: (filtros: Record<string, unknown>) => [...recursoKeys.misDocumentos(), "lista", filtros] as const,
  proceso: (procesoId: number) => [...recursoKeys.misDocumentos(), "proceso", procesoId] as const,
  /** Concepto del técnico (Mis informes, C.4): cuelga de Mis informes. */
  concepto: (conceptoId: number) => [...recursoKeys.misDocumentos(), "concepto", conceptoId] as const,
  tecnicos: () => [...recursoKeys.all, "tecnicos"] as const,
  abogados: () => [...recursoKeys.all, "abogados"] as const,
};
