import type { ExpedienteDatos, ExpedienteDetalle, UsoAgua } from "../../types";

/**
 * Estado del formulario de información base (alta y edición). Textos tal
 * cual se escriben; el payload se arma con `construirExpedienteDatos`.
 */
export type ExpedienteFormState = {
  radicado: string;
  fecha_radicado: string;
  expediente: string;
  numero_vital: string;
  nombre_predio: string;
  matricula_inmobiliaria: string;
  codigo_catastral: string;
  radicado_oficio_entrada: string;
  fecha_oficio_entrada: string;
  municipio_id: number;
  vereda_id: number;
  tipo_fuente_id: number;
  nombre_fuente: string;
  fuente_ids: number[];
  usos: UsoAgua[];
  /** Comprobante ya guardado (edición). */
  doc_comprobante_pago_id: number | null;
  /** PDF nuevo elegido en el formulario (se sube a app-docs al guardar). */
  comprobante: File | null;
};

/** Campos de texto libre con longitud máxima del backend (API.md A.3). */
export const MAX_LONGITUD = {
  radicado: 15,
  expediente: 9,
  numero_vital: 20,
  nombre_predio: 50,
  matricula_inmobiliaria: 20,
  codigo_catastral: 30,
  radicado_oficio_entrada: 20,
  nombre_fuente: 50,
} as const;

export type CampoTextoExpediente = keyof typeof MAX_LONGITUD;

export const FORM_VACIO: ExpedienteFormState = {
  radicado: "",
  fecha_radicado: "",
  expediente: "",
  numero_vital: "",
  nombre_predio: "",
  matricula_inmobiliaria: "",
  codigo_catastral: "",
  radicado_oficio_entrada: "",
  fecha_oficio_entrada: "",
  municipio_id: 0,
  vereda_id: 0,
  tipo_fuente_id: 0,
  nombre_fuente: "",
  fuente_ids: [],
  usos: [],
  doc_comprobante_pago_id: null,
  comprobante: null,
};

const ETIQUETAS: Record<CampoTextoExpediente, string> = {
  radicado: "el radicado",
  expediente: "el número de expediente",
  numero_vital: "el número VITAL",
  nombre_predio: "el nombre del predio",
  matricula_inmobiliaria: "la matrícula inmobiliaria",
  codigo_catastral: "el código catastral",
  radicado_oficio_entrada: "el radicado de la solicitud",
  nombre_fuente: "el nombre de la fuente",
};

/** Estado inicial de edición a partir del detalle del backend. */
export function formDesdeDetalle(d: ExpedienteDetalle): ExpedienteFormState {
  return {
    radicado: d.radicado ?? "",
    fecha_radicado: d.fecha_radicado ?? "",
    expediente: d.expediente ?? "",
    numero_vital: d.numero_vital ?? "",
    nombre_predio: d.nombre_predio ?? "",
    matricula_inmobiliaria: d.matricula_inmobiliaria ?? "",
    codigo_catastral: d.codigo_catastral ?? "",
    radicado_oficio_entrada: d.radicado_oficio_entrada ?? "",
    fecha_oficio_entrada: d.fecha_oficio_entrada ?? "",
    municipio_id: d.municipio?.id ?? 0,
    vereda_id: d.vereda?.id ?? 0,
    tipo_fuente_id: d.tipo_fuente?.id ?? 0,
    nombre_fuente: d.nombre_fuente ?? "",
    fuente_ids: (d.fuentes ?? []).map((f) => f.id),
    usos: [...(d.usos ?? [])],
    doc_comprobante_pago_id: d.doc_comprobante_pago_id ?? null,
    comprobante: null,
  };
}

const capitalizar = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** El comprobante debe ser PDF (el backend también lo valida). */
export function esPdf(archivo: { name: string; type: string }): boolean {
  return archivo.type === "application/pdf" || archivo.name.toLowerCase().endsWith(".pdf");
}

/**
 * Validación del lado del cliente (solo forma: obligatorios, longitudes y
 * PDF). Las reglas de negocio (unicidad, catálogos) las valida el backend.
 * Devuelve el primer error o `null`.
 */
export function validarExpedienteForm(f: ExpedienteFormState): string | null {
  for (const campo of Object.keys(MAX_LONGITUD) as CampoTextoExpediente[]) {
    const v = f[campo].trim();
    if (!v) return `Ingrese ${ETIQUETAS[campo]}`;
    if (v.length > MAX_LONGITUD[campo]) {
      return `${capitalizar(ETIQUETAS[campo])} admite máximo ${MAX_LONGITUD[campo]} caracteres`;
    }
  }
  if (!f.fecha_radicado) return "Seleccione la fecha de radicado";
  if (!f.fecha_oficio_entrada) return "Seleccione la fecha de la solicitud";
  if (!f.municipio_id) return "Seleccione un municipio";
  if (!f.vereda_id) return "Seleccione una vereda";
  if (!f.tipo_fuente_id) return "Seleccione el tipo de fuente";
  if (f.fuente_ids.length === 0) return "Seleccione al menos una fuente";
  if (f.usos.length === 0) return "Seleccione al menos un uso del agua";
  if (!f.comprobante && !f.doc_comprobante_pago_id) return "Adjunte el comprobante de pago (PDF)";
  if (f.comprobante && !esPdf(f.comprobante)) return "El comprobante de pago debe ser un PDF";
  return null;
}

/** Body `ExpedienteDatos` (textos recortados, listas sin repetidos). */
export function construirExpedienteDatos(f: ExpedienteFormState, docComprobanteId: number): ExpedienteDatos {
  return {
    radicado: f.radicado.trim(),
    fecha_radicado: f.fecha_radicado,
    expediente: f.expediente.trim(),
    numero_vital: f.numero_vital.trim(),
    nombre_predio: f.nombre_predio.trim(),
    matricula_inmobiliaria: f.matricula_inmobiliaria.trim(),
    codigo_catastral: f.codigo_catastral.trim(),
    radicado_oficio_entrada: f.radicado_oficio_entrada.trim(),
    fecha_oficio_entrada: f.fecha_oficio_entrada,
    doc_comprobante_pago_id: docComprobanteId,
    vereda_id: f.vereda_id,
    tipo_fuente_id: f.tipo_fuente_id,
    nombre_fuente: f.nombre_fuente.trim(),
    fuente_ids: [...new Set(f.fuente_ids)],
    usos: [...new Set(f.usos)],
  };
}

/** Agrega o quita un valor de una lista (checkbox múltiple). */
export function alternar<T>(lista: T[], valor: T): T[] {
  return lista.includes(valor) ? lista.filter((v) => v !== valor) : [...lista, valor];
}
