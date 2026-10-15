import type { EtapasExpediente } from "../types";

/**
 * Pestañas del detalle del expediente en el orden del plan (§4):
 * Información base → Auto admite → Concepto técnico → Requerimiento →
 * Decisión (con recurso) → Memorias de cálculo → Recibo de obras. El tercero
 * interviniente no es una etapa: vive en "Información base", debajo de los
 * solicitantes. `icon` es una clase de boxicons, como en infraction.
 */
export const ETAPAS_RECURSO = [
  { id: "info", label: "Información base", icon: "bx-info-circle" },
  { id: "auto-admite", label: "Auto que admite", icon: "bx-file" },
  { id: "concepto", label: "Concepto técnico", icon: "bx-book-bookmark" },
  { id: "requerimiento", label: "Requerimiento", icon: "bx-error-alt" },
  { id: "decision", label: "Decisión", icon: "bx-check-shield" },
  { id: "memorias", label: "Memorias de cálculo", icon: "bx-calculator" },
  { id: "obras", label: "Recibo de obras", icon: "bx-wrench" },
] as const;

export type EtapaTabId = (typeof ETAPAS_RECURSO)[number]["id"];

/**
 * ¿La pestaña tiene algo que mostrar? En Consulta se deshabilitan las etapas
 * que no existen (como en infraction). Información base siempre.
 */
export function pestanaConDatos(id: EtapaTabId, etapas: EtapasExpediente | null | undefined): boolean {
  if (id === "info") return true;
  if (!etapas) return false;
  switch (id) {
    case "auto-admite":
      return !!etapas.admite?.existe;
    case "concepto":
      return !!etapas.concepto?.existe;
    case "requerimiento":
      return !!etapas.requerimiento?.existe;
    case "decision":
      return !!etapas.decision?.existe;
    case "memorias":
      return !!etapas.memorias?.existe;
    case "obras":
      return !!etapas.obras?.existe;
  }
}

/** `etapa_padre` (C.12, Mis informes / detalle del proceso) → pestaña. */
const POR_ETAPA_PADRE: Record<string, EtapaTabId> = {
  acto_admite: "auto-admite",
  concepto_tecnico: "concepto",
  requerimiento: "requerimiento",
  decision: "decision",
  memorias_calculo: "memorias",
  recibo_satisfaccion_obras: "obras",
  tercero_interviniente: "info",
};

/** `etapa_tipo` del backend (B.1/B.2) → pestaña. */
const POR_ETAPA_TIPO: Record<string, EtapaTabId> = {
  acto_admite: "auto-admite",
  concepto_tecnico: "concepto",
  requerimiento: "requerimiento",
  decision: "decision",
  recurso_reposicion: "decision",
  memorias_calculo: "memorias",
  recibo_satisfaccion_obras: "obras",
  expediente_involucrado: "info",
};

/**
 * `tipo_documento` → pestaña, para los documentos cuya `etapa_tipo` no dice
 * a qué etapa pertenecen (un concepto técnico puede ser de la etapa 2, del
 * requerimiento, de memorias o de obras).
 */
const POR_TIPO_DOCUMENTO: Record<string, EtapaTabId> = {
  CONCEPTO_ETAPA2: "concepto",
  CONCEPTO_ADICIONAL: "requerimiento",
  CONCEPTO_MEMORIAS: "memorias",
  CONCEPTO_SUBSANACION: "memorias",
  APRUEBA_MEMORIAS: "memorias",
  CONCEPTO_OBRAS: "obras",
  CONCEPTO_OBRAS_SEGUNDO: "obras",
  APRUEBA_OBRAS: "obras",
  RECONOCE_TERCERO: "info",
};

/**
 * Pestaña donde vive un documento de revisión. Manda `etapa_padre` (C.12),
 * que ya distingue p. ej. el requerimiento de memorias del de la etapa 3; si
 * no llega, se deduce por tipo de documento y `etapa_tipo`.
 */
export function pestanaDeDocumento(
  etapaTipo: string | null | undefined,
  tipoDocumento?: string | null,
  etapaPadre?: string | null,
): EtapaTabId {
  if (etapaPadre && POR_ETAPA_PADRE[etapaPadre]) return POR_ETAPA_PADRE[etapaPadre];
  if (tipoDocumento && POR_TIPO_DOCUMENTO[tipoDocumento]) return POR_TIPO_DOCUMENTO[tipoDocumento];
  if (etapaTipo && POR_ETAPA_TIPO[etapaTipo]) return POR_ETAPA_TIPO[etapaTipo];
  return "info";
}

/** Valida un id de pestaña que llega por navegación. */
export function esPestana(valor: unknown): valor is EtapaTabId {
  return ETAPAS_RECURSO.some((e) => e.id === valor);
}
