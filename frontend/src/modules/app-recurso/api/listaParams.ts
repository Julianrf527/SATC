/**
 * Filtros del listado de expedientes (GET /recurso/expedientes, API.md A.2).
 * Todos se resuelven en el backend: el listado es paginado.
 */
export type FiltrosListaExpedientes = {
  /** Texto libre: se busca como radicado. */
  radicado: string;
  /** Número de expediente, p. ej. "CA 001". */
  expediente: string;
  numero_vital: string;
  municipio_id: number;
  vereda_id: number;
  /** id de app-involved (se resuelve antes buscando la persona por documento). */
  involucrado_id: number | null;
  page: number;
  limit: number;
};

export const FILTROS_LISTA_INICIALES: FiltrosListaExpedientes = {
  radicado: "",
  expediente: "",
  numero_vital: "",
  municipio_id: 0,
  vereda_id: 0,
  involucrado_id: null,
  page: 1,
  limit: 20,
};

/** Query string del listado: omite vacíos y recorta textos. */
export function construirQueryLista(f: FiltrosListaExpedientes): string {
  const params = new URLSearchParams();
  params.set("page", String(Math.max(1, f.page)));
  params.set("limit", String(Math.min(200, Math.max(1, f.limit))));
  const textos: [string, string][] = [
    ["radicado", f.radicado],
    ["expediente", f.expediente],
    ["numero_vital", f.numero_vital],
  ];
  for (const [clave, valor] of textos) {
    const v = valor.trim();
    if (v) params.set(clave, v);
  }
  if (f.municipio_id > 0) params.set("municipio_id", String(f.municipio_id));
  if (f.vereda_id > 0) params.set("vereda_id", String(f.vereda_id));
  if (f.involucrado_id !== null && f.involucrado_id > 0) params.set("involucrado_id", String(f.involucrado_id));
  return params.toString();
}

/** Número de filtros activos (sin contar paginación). */
export function contarFiltrosActivos(f: FiltrosListaExpedientes): number {
  return [
    f.radicado.trim(),
    f.expediente.trim(),
    f.numero_vital.trim(),
    f.municipio_id > 0,
    f.vereda_id > 0,
    f.involucrado_id !== null,
  ].filter(Boolean).length;
}

/** Total de páginas (al menos 1). */
export function totalPaginas(totalCount: number, limit: number): number {
  return Math.max(1, Math.ceil(totalCount / Math.max(1, limit)));
}
