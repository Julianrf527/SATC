// Validaciones y conversiones compartidas por los formularios de etapas.

/** Numerado de un acto: entero 1..9999 (máx. 4 dígitos, C "Numerado"). */
export function numeradoValido(numerado: string): boolean {
  const v = numerado.trim();
  return /^\d{1,4}$/.test(v) && Number(v) > 0;
}

/** El backend acepta `"0012"`: se envía con ceros a la izquierda, como infraction. */
export function numeradoParaEnviar(numerado: string): string {
  return numerado.trim().padStart(4, "0");
}

/** Número decimal ≥ 0 escrito por el usuario (acepta coma decimal). `null` si está vacío o no es válido. */
export function decimal(valor: string): number | null {
  const v = valor.trim().replace(",", ".");
  if (!v) return null;
  const n = Number(v);
  return Number.isFinite(n) && n >= 0 ? n : null;
}

/** Entero ≥ 0. `null` si está vacío o no es válido. */
export function entero(valor: string): number | null {
  const v = valor.trim();
  if (!/^\d+$/.test(v)) return null;
  return Number(v);
}

/** Fecha `YYYY-MM-DD`. */
export function fechaValida(valor: string): boolean {
  return /^\d{4}-\d{2}-\d{2}$/.test(valor);
}

/** Todo documento de etapa debe ser PDF (entra a la descarga del expediente). */
export function esPdf(archivo: File): boolean {
  return archivo.type === "application/pdf" || archivo.name.toLowerCase().endsWith(".pdf");
}

export const hoy = () => new Date().toISOString().split("T")[0];

/** Forma del acto: Auto o Resolución. La elige quien carga o corrige el acto. */
export type ClaseActo = "AUTO" | "RES";

export const OPCIONES_CLASE_ACTO: { value: ClaseActo; label: string }[] = [
  { value: "AUTO", label: "AUTO" },
  { value: "RES", label: "RES" },
];
