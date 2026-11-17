/**
 * Etapas del proceso de infracción en orden. `codigo` es el que devuelve el
 * backend en `etapa_actual` / `ultima_etapa` (services/etapa_actual.py: la
 * etapa más avanzada que existe); `etiqueta` es el único lugar donde se
 * traduce a texto (pestañas, "Última etapa", filtro rápido).
 */
export const ETAPAS_PROCESO = [
  { codigo: "respuesta", etiqueta: "Respuesta" },
  { codigo: "visita", etiqueta: "Visita Técnica" },
  { codigo: "concepto", etiqueta: "Acoger Concepto" },
  { codigo: "seguimiento", etiqueta: "Visita Seguimiento" },
  { codigo: "cierre", etiqueta: "Cierre Expediente" },
] as const;

export type CodigoEtapa = (typeof ETAPAS_PROCESO)[number]["codigo"];

export const ETIQUETA_ETAPA = Object.fromEntries(
  ETAPAS_PROCESO.map((e) => [e.codigo, e.etiqueta]),
) as Record<CodigoEtapa, string>;

/** Etiqueta de un código de etapa (o el valor tal cual si no se reconoce). */
export function etiquetaEtapa(codigo: string | null | undefined): string | null {
  if (!codigo) return null;
  return ETAPAS_PROCESO.find((e) => e.codigo === codigo)?.etiqueta ?? codigo;
}
