// Trazos SVG (viewBox 24x24, stroke) usados por las etapas del sancionatorio.
export const ICONOS = {
  documento:
    "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  alerta:
    "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z",
  checkCirculo: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
  escudo:
    "M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z",
  portapapeles:
    "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4",
  editar:
    "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z",
  guardar: "M5 13l4 4L19 7",
  info: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  etiqueta:
    "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z",
  corazon:
    "M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z",
  numeral: "M7 20l4-16m2 16l4-16M6 9h14M4 15h14",
  papelera:
    "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
  archivar:
    "M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4",
  mas: "M12 6v6m0 0v6m0-6h6m-6 0H6",
} as const;

/** Icono de documento relleno (viewBox 20x20) de los botones "ver documento". */
export const PDF_RELLENO_20 =
  "M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z";

/** Icono PDF relleno (viewBox 24x24). */
export const PDF_RELLENO_24 =
  "M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M15.5,15.5L13,19L11.5,15.5L8,14L11.5,12.5L13,9L14.5,12.5L18,14L15.5,15.5M13,3.5L17.5,8H13V3.5Z";

/** Tonos daisyUI de las tarjetas de datos de etapa (clases literales para Tailwind). */
export const TONOS = {
  info: { fondo: "bg-info/10", texto: "text-info", hover: "text-info hover:bg-info/10", boton: "btn-info" },
  warning: { fondo: "bg-warning/10", texto: "text-warning", hover: "text-warning hover:bg-warning/10", boton: "btn-warning" },
  error: { fondo: "bg-error/10", texto: "text-error", hover: "text-error hover:bg-error/10", boton: "btn-error" },
  primary: { fondo: "bg-primary/10", texto: "text-primary", hover: "hover:bg-primary/10", boton: "btn-primary" },
  success: { fondo: "bg-success/10", texto: "text-success", hover: "text-success hover:bg-success/10", boton: "btn-success" },
} as const;

export type Tono = keyof typeof TONOS;
