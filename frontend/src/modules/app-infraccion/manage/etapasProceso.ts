/**
 * Etapas del proceso de infracción en orden. `codigo` es el que devuelve el
 * backend en `etapa_actual` / `ultima_etapa` (services/etapa_actual.py: la
 * etapa más avanzada que existe); `etiqueta` es el único lugar donde se
 * traduce a texto (pestañas, "Última etapa", filtro rápido).
 */
export const ETAPAS_PROCESO = [
  { codigo: "respuesta", etiqueta: "Respuesta", icono: "bx-search-alt" },
  { codigo: "visita", etiqueta: "Visita Técnica", icono: "bx-error-alt" },
  { codigo: "concepto", etiqueta: "Acoger Concepto", icono: "bx-book-bookmark" },
  { codigo: "seguimiento", etiqueta: "Visita Seguimiento", icono: "bx-error-alt" },
  { codigo: "concepto_seguimiento", etiqueta: "Acoger Concepto · Seguimiento", icono: "bx-book-bookmark" },
  { codigo: "cierre", etiqueta: "Cierre Expediente", icono: "bx-check-circle" },
] as const;

export type CodigoEtapa = (typeof ETAPAS_PROCESO)[number]["codigo"];

export const ETIQUETA_ETAPA = Object.fromEntries(
  ETAPAS_PROCESO.map((e) => [e.codigo, e.etiqueta]),
) as Record<CodigoEtapa, string>;

/**
 * Título del recuadro principal de cada etapa, con su número (como recurso:
 * "Etapa 1 · Auto que admite"). Las etapas son fijas: viven aquí, no en el backend.
 */
export const TITULO_ETAPA = Object.fromEntries(
  ETAPAS_PROCESO.map((e, i) => [e.codigo, `Etapa ${i + 1} · ${e.etiqueta}`]),
) as Record<CodigoEtapa, string>;

/** Etiqueta de un código de etapa (o el valor tal cual si no se reconoce). */
export function etiquetaEtapa(codigo: string | null | undefined): string | null {
  if (!codigo) return null;
  return ETAPAS_PROCESO.find((e) => e.codigo === codigo)?.etiqueta ?? codigo;
}
