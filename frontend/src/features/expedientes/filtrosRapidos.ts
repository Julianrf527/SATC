import type { ExpedienteBase, FiltroRapido } from "./types";

/** Select de municipio con las opciones presentes en la lista (orden de aparición). */
export function filtroMunicipio<T extends ExpedienteBase>(): FiltroRapido<T> {
  return {
    id: "municipio",
    tipo: "derivado",
    etiquetaTodos: "Todos los municipios",
    valor: (e) => e.municipio?.nombre,
  };
}

/** Select archivados / activos. */
export function filtroArchivado<T extends ExpedienteBase>(etiquetaTodos: string): FiltroRapido<T> {
  return {
    id: "archivado",
    tipo: "fijo",
    etiquetaTodos,
    opciones: [
      { value: "archived", label: "Solo archivados" },
      { value: "active", label: "Solo activos" },
    ],
    coincide: (e, v) => (v === "archived" ? e.archivado === true : e.archivado === false),
  };
}

/** Select cuyas opciones (ordenadas) salen de un campo del expediente. */
export function filtroPorCampo<T>(
  id: string,
  etiquetaTodos: string,
  valor: (e: T) => string | null | undefined,
): FiltroRapido<T> {
  return { id, tipo: "derivado", etiquetaTodos, valor, ordenar: true };
}
