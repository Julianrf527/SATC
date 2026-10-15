/** Filtros y paginación de Mis informes (B.2). Se resuelven en el backend. */
export type RolMisDocumentos = "" | "encargado" | "revisor";

export type FiltrosMisDocumentos = {
  expediente: string;
  tipo_documento: string;
  rol: RolMisDocumentos;
  estado: string;
  /** Casilla "Solo los que requieren mi acción". */
  soloAccion: boolean;
};

export const FILTROS_MIS_DOCUMENTOS: FiltrosMisDocumentos = {
  expediente: "",
  tipo_documento: "",
  rol: "",
  estado: "",
  soloAccion: false,
};

/** Tamaño de página (mismo default que el listado de informes de infraction). */
export const LIMITE_MIS_DOCUMENTOS = 20;

export function hayFiltrosActivos(f: FiltrosMisDocumentos): boolean {
  return f.expediente.trim() !== "" || f.tipo_documento !== "" || f.rol !== "" || f.estado !== "" || f.soloAccion;
}

/** Query string de GET /recurso/mis-documentos. */
export function construirQueryMisDocumentos(
  f: FiltrosMisDocumentos,
  page = 1,
  limit = LIMITE_MIS_DOCUMENTOS,
): string {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (f.expediente.trim()) params.set("expediente", f.expediente.trim());
  if (f.tipo_documento) params.set("tipo_documento", f.tipo_documento);
  if (f.rol) params.set("rol", f.rol);
  if (f.estado) params.set("estado", f.estado);
  if (f.soloAccion) params.set("solo_accion", "true");
  return params.toString();
}

/** Números de página a mostrar (ventana de hasta `max` alrededor de la actual). */
export function paginasVisibles(page: number, totalPages: number, max = 7): number[] {
  const total = Math.max(1, totalPages);
  const n = Math.min(max, total);
  const inicio = Math.min(Math.max(1, page - Math.floor(n / 2)), total - n + 1);
  return Array.from({ length: n }, (_, i) => inicio + i);
}

const ETIQUETAS_ROL: Record<string, string> = { encargado: "Encargado", revisor: "Revisor" };

/** Etiqueta de un rol de la fila (B.2: `roles`). */
export function etiquetaRol(rol: string): string {
  return ETIQUETAS_ROL[rol] ?? rol;
}
