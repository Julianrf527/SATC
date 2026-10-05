import { parseDate } from "@shared/lib/format";

/** Etiquetas cortas de los tipos de alerta (claves de ambos servicios). */
export const TIPO_LABELS: Record<string, string> = {
  inicio_sancionatorio: "Inicio Sancionatorio",
  decision_fondo: "Decisión de Fondo",
  presentacion_descargos: "Descargos",
  informe_tecnico: "Informe Técnico",
  alegato_conclusion: "Alegato",
  presentacion_recurso: "Recurso",
  resolucion_recurso: "Resolución",
  notificacion_recurso: "Notificación",
  respuesta_plazo: "Plazo Respuesta",
  concepto_constancia: "Constancia Citación",
  concepto_termino: "Término Concepto",
};

export const URGENCIA_ORDER: Record<string, number> = { critico: 0, alta: 1, media: 2, baja: 3 };

/**
 * Fecha corta es-CO ("5 ene." / "5 ene. 2026"). Usa `parseDate` para que las
 * fechas sin hora no se muestren un día antes (new Date("aaaa-mm-dd") es UTC).
 */
export function formatFechaCorta(f: string, withYear = false): string {
  const d = parseDate(f);
  if (!d) return f;
  return d.toLocaleDateString("es-CO", {
    ...(withYear ? { year: "numeric" } : {}),
    month: "short",
    day: "numeric",
  });
}
