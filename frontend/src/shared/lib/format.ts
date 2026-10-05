/**
 * Formateadores de presentación (es-CO). Reemplazan las ~18 copias locales de
 * `formatDate` / `formatFileSize` que había en los componentes.
 *
 * Equivalencias con las versiones antiguas:
 *  - split("-") -> `${d}/${m}/${y}`             => formatDate(v)                 "05/01/2026"
 *  - toLocaleDateString("es-ES", 2-digit)        => formatDate(v)                 "05/01/2026"
 *  - "5 de enero de 2026" (array de meses)       => formatDate(v, { style: "long" })
 *  - toLocaleString("es-CO", ... hour, minute)   => formatDateTime(v)             "05/01/2026, 02:30 p. m."
 *  - idem con second: "2-digit"                  => formatDateTime(v, { seconds: true })
 *  - "No registrada" / "-" como vacío            => pasar `fallback`
 */

export type DateInput = string | number | Date | null | undefined;

const DATE_ONLY = /^(\d{4})-(\d{1,2})-(\d{1,2})$/;

const MESES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

/**
 * Convierte la entrada a Date. Las fechas sin hora ("2026-01-05", lo que
 * devuelve el backend para columnas DATE) se interpretan en hora LOCAL: con
 * `new Date("2026-01-05")` JS asume UTC y en Colombia (UTC-5) se mostraría el
 * día anterior.
 */
export function parseDate(value: DateInput): Date | null {
  if (value === null || value === undefined || value === "") return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  if (typeof value === "string") {
    const m = DATE_ONLY.exec(value.trim());
    if (m) return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  }
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

const pad2 = (n: number) => String(n).padStart(2, "0");

export type FormatDateOptions = {
  /** "short" = dd/mm/aaaa (por defecto) · "long" = "5 de enero de 2026" */
  style?: "short" | "long";
  /** Texto para valores vacíos o inválidos. Por defecto "—". */
  fallback?: string;
};

/** Fecha sin hora. `formatDate("2026-01-05")` → "05/01/2026". */
export function formatDate(value: DateInput, options: FormatDateOptions = {}): string {
  const { style = "short", fallback = "—" } = options;
  const d = parseDate(value);
  if (!d) return fallback;
  if (style === "long") return `${d.getDate()} de ${MESES[d.getMonth()]} de ${d.getFullYear()}`;
  return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
}

export type FormatDateTimeOptions = {
  /** Incluir segundos (vista de auditoría). */
  seconds?: boolean;
  fallback?: string;
};

/** Fecha y hora locales es-CO. `formatDateTime(iso)` → "05/01/2026, 02:30 p. m.". */
export function formatDateTime(value: DateInput, options: FormatDateTimeOptions = {}): string {
  const { seconds = false, fallback = "—" } = options;
  const d = parseDate(value);
  if (!d) return fallback;
  return d.toLocaleString("es-CO", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    ...(seconds ? { second: "2-digit" } : {}),
  });
}

/** Tamaño legible en base 1024. `formatFileSize(1536)` → "1.5 KB". */
export function formatFileSize(bytes: number | null | undefined, fallback = "—"): string {
  if (bytes === null || bytes === undefined || !Number.isFinite(bytes) || bytes < 0) return fallback;
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + " GB";
}
