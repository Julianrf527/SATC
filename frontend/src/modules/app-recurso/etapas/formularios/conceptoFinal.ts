// "Cargar versión final" de un concepto técnico (`ConceptoFinal`, C.4).
import type { DatosConcepto, TipoConcepto } from "../../types";
import { decimal, entero, esPdf, fechaValida } from "./comunes";

export type CampoConcepto =
  | "file_id"
  | "fecha_aceptacion"
  | "fecha_visita_tecnica"
  | "caudal_fuente"
  | "caudal_disponible"
  | "caudal_otorgado"
  | "num_usuarios"
  | "cumple";

/** Campos de datos del formulario (todo menos el archivo). */
export type CampoDatoConcepto = Exclude<CampoConcepto, "file_id">;

export type CamposConcepto = { obligatorios: string[]; opcionales: string[] };

const CAUDALES = ["caudal_fuente", "caudal_disponible", "caudal_otorgado", "num_usuarios"];

/**
 * Campos por tipo (C.4). En Mis informes el backend los manda en `campos`
 * (GET /etapas/conceptos/{id}); en el árbol no, así que se usa esta tabla,
 * que replica la del backend.
 */
export function camposConcepto(tipo: TipoConcepto): CamposConcepto {
  const base = ["file_id", "fecha_aceptacion"];
  switch (tipo) {
    case "etapa2":
      return { obligatorios: [...base, ...CAUDALES], opcionales: [] };
    case "adicional":
      return { obligatorios: base, opcionales: CAUDALES };
    case "memorias":
    case "subsanacion":
      return { obligatorios: [...base, "cumple"], opcionales: [] };
    case "obras":
    case "obras_segundo":
      return { obligatorios: [...base, "cumple", "fecha_visita_tecnica"], opcionales: [] };
  }
}

export const ETIQUETAS_CAMPO_CONCEPTO: Record<CampoConcepto, string> = {
  file_id: "Concepto firmado (PDF)",
  fecha_aceptacion: "Fecha del concepto (firma)",
  fecha_visita_tecnica: "Fecha de visita técnica",
  caudal_fuente: "Caudal fuente (L/s)",
  caudal_disponible: "Caudal disponible (L/s)",
  caudal_otorgado: "Caudal otorgado (L/s)",
  num_usuarios: "Número de usuarios",
  cumple: "¿Cumple?",
};

export type ConceptoFinalForm = {
  archivo: File | null;
  fecha_aceptacion: string;
  fecha_visita_tecnica: string;
  caudal_fuente: string;
  caudal_disponible: string;
  caudal_otorgado: string;
  num_usuarios: string;
  cumple: boolean | null;
};

const texto = (v: number | null | undefined) => (v === null || v === undefined ? "" : String(v));

/** Estado inicial con los datos que ya tenga el concepto (p. ej. la fecha de visita del auto). */
export function conceptoFinalInicial(datos?: Partial<DatosConcepto> | null): ConceptoFinalForm {
  return {
    archivo: null,
    fecha_aceptacion: datos?.fecha_aceptacion ?? "",
    fecha_visita_tecnica: datos?.fecha_visita_tecnica ?? "",
    caudal_fuente: texto(datos?.caudal_fuente),
    caudal_disponible: texto(datos?.caudal_disponible),
    caudal_otorgado: texto(datos?.caudal_otorgado),
    num_usuarios: texto(datos?.num_usuarios),
    cumple: datos?.cumple ?? null,
  };
}

/** Campos del formulario que se muestran (obligatorios + opcionales, sin el archivo). */
export function camposVisibles(campos: CamposConcepto): CampoDatoConcepto[] {
  return [...campos.obligatorios, ...campos.opcionales].filter(
    (c): c is CampoDatoConcepto => c !== "file_id" && c in ETIQUETAS_CAMPO_CONCEPTO,
  );
}

function valorCampo(f: ConceptoFinalForm, campo: CampoDatoConcepto): unknown {
  switch (campo) {
    case "fecha_aceptacion":
    case "fecha_visita_tecnica":
      return fechaValida(f[campo]) ? f[campo] : null;
    case "num_usuarios":
      return entero(f.num_usuarios);
    case "cumple":
      return f.cumple;
    default:
      return decimal(f[campo]);
  }
}

const vacio = (f: ConceptoFinalForm, campo: CampoDatoConcepto) =>
  campo === "cumple" ? f.cumple === null : !f[campo].trim();

export function validarConceptoFinal(f: ConceptoFinalForm, campos: CamposConcepto): string | null {
  if (!f.archivo) return "Adjunte el concepto firmado (PDF)";
  if (!esPdf(f.archivo)) return "El concepto firmado debe ser PDF";
  return validarCamposConcepto(f, campos);
}

/** Valida los datos del concepto (sin el archivo): obligatorios con valor y formatos. */
export function validarCamposConcepto(f: ConceptoFinalForm, campos: CamposConcepto): string | null {
  for (const campo of camposVisibles(campos)) {
    const obligatorio = campos.obligatorios.includes(campo);
    if (vacio(f, campo)) {
      if (obligatorio) return `Complete: ${ETIQUETAS_CAMPO_CONCEPTO[campo]}`;
      continue;
    }
    if (valorCampo(f, campo) === null) return `Valor inválido: ${ETIQUETAS_CAMPO_CONCEPTO[campo]}`;
  }
  return null;
}

/** Body de `.../version-final` del concepto: solo los campos del tipo con valor. */
export function bodyConceptoFinal(f: ConceptoFinalForm, campos: CamposConcepto, fileId: number): Record<string, unknown> {
  const body: Record<string, unknown> = { file_id: fileId };
  for (const campo of camposVisibles(campos)) {
    const v = valorCampo(f, campo);
    if (v !== null) body[campo] = v;
  }
  return body;
}
