// Lógica pura de la pestaña Alertas paginada en el servidor: construcción de
// la URL (alcance + página + filtros) y textos de la paginación.
import { endpointConAlcance, type AlcanceAlertas } from "./alertasAlcance";
import type { EstadoSemaforo } from "./types";

/** Alertas por página (el backend admite hasta 100). */
export const ALERTAS_POR_PAGINA = 10;

/** Espera tras teclear el radicado antes de consultar (como gestion-encargado). */
export const DEBOUNCE_RADICADO_MS = 400;

/** Valor de los selectores Estado / Tipo que significa "sin filtro". */
export const TODOS = "all";

export type FiltrosAlertas = {
  alcance: AlcanceAlertas;
  page: number;
  limit: number;
  /** Parcial, sin distinguir mayúsculas (lo resuelve el backend). */
  radicado: string;
  estado: EstadoSemaforo | typeof TODOS;
  tipo: string;
};

/**
 * URL de una página de alertas. `alcance=mios` no se envía (es el valor por
 * defecto del backend); los filtros vacíos o "all" tampoco.
 */
export function urlAlertasPaginadas(endpoint: string, f: FiltrosAlertas): string {
  const params = new URLSearchParams();
  params.set("page", String(f.page));
  params.set("limit", String(f.limit));
  const radicado = f.radicado.trim();
  if (radicado) params.set("radicado", radicado);
  if (f.estado !== TODOS) params.set("estado", f.estado);
  if (f.tipo && f.tipo !== TODOS) params.set("tipo", f.tipo);
  const base = endpointConAlcance(endpoint, f.alcance);
  return `${base}${base.includes("?") ? "&" : "?"}${params.toString()}`;
}

/** Páginas a mostrar en "Página X de Y" (mínimo 1, como antes). */
export function paginasVisibles(totalPages: number | undefined): number {
  return Math.max(1, totalPages ?? 0);
}

/** "Mostrando N de M alertas". */
export function textoMostrando(enPagina: number, total: number): string {
  return `Mostrando ${enPagina} de ${total} alerta${total !== 1 ? "s" : ""}`;
}
