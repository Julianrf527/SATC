import type { ResumenProcesoInforme } from "../types";

type ConEstado = ResumenProcesoInforme & { aceptado: boolean };

/**
 * Clave para filtrar por estado sin hardcodear códigos del proceso. Un informe
 * aceptado se muestra "Aceptado" venga del flujo o del cargue manual; el
 * estado del proceso solo se muestra mientras el informe no esté aceptado.
 */
export const claveEstado = (informe: ConEstado): string =>
  informe.aceptado ? "__aceptado" : (informe.estado_proceso?.codigo ?? "__sin_proceso");

const etiquetaEstado = (informe: ConEstado): string =>
  informe.aceptado ? "Aceptado" : (informe.estado_proceso?.etiqueta ?? "Sin proceso");

/** Opciones del filtro "Estado" a partir de los estados que llegaron en la lista. */
export function opcionesEstado(informes: ConEstado[]): { value: string; label: string }[] {
  const vistas = new Map<string, string>();
  for (const inf of informes) vistas.set(claveEstado(inf), etiquetaEstado(inf));
  return [...vistas].map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label));
}
