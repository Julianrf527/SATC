// "Cargar versión final" de un concepto técnico (`ConceptoFinal`, C.4).
// Qué datos pide cada tipo de concepto (obligatorio, tipo, etiqueta) NO vive
// aquí: llega del backend en `campos` (nodo de concepto del árbol y
// GET /etapas/conceptos/{id}). Este módulo solo guarda el estado del
// formulario, valida y arma el body según esa definición.
import type { CampoConceptoDef, CamposConcepto, DatosConcepto } from "../../types";
import { decimal, entero, esPdf, fechaValida } from "./comunes";

export type { CamposConcepto } from "../../types";

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

/** Datos del formulario (todo menos el archivo): columnas del concepto que se pueden diligenciar. */
export type CampoDatoConcepto = Exclude<keyof ConceptoFinalForm, "archivo">;

/** Definición de un campo que el formulario sabe guardar. */
export type CampoVisible = CampoConceptoDef & { campo: CampoDatoConcepto };

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

const CLAVES_FORM = new Set<string>(Object.keys(conceptoFinalInicial()).filter((k) => k !== "archivo"));

/** Campos del backend que se muestran (sin el archivo), en su orden. Ignora los que el formulario no conoce. */
export function camposVisibles(campos: CamposConcepto): CampoVisible[] {
  return campos.campos.filter((c): c is CampoVisible => CLAVES_FORM.has(c.campo));
}

/** La misma definición con todo opcional (cargue directo de super gestión: se envía solo lo diligenciado). */
export function soloOpcionales(campos: CamposConcepto): CamposConcepto {
  return {
    obligatorios: [],
    opcionales: [...campos.obligatorios, ...campos.opcionales].filter((c) => c !== "file_id"),
    campos: campos.campos.map((c) => ({ ...c, obligatorio: false })),
  };
}

/** Valor de texto del campo (fechas y números se guardan como texto en el formulario). */
export function textoCampo(f: ConceptoFinalForm, campo: CampoDatoConcepto): string {
  const v = f[campo];
  return typeof v === "string" ? v : "";
}

/** Valor sí/no del campo. */
export function siNoCampo(f: ConceptoFinalForm, campo: CampoDatoConcepto): boolean | null {
  const v = f[campo];
  return typeof v === "boolean" ? v : null;
}

/** Valor listo para enviar según el tipo del backend, o `null` si está vacío o es inválido. */
function valorCampo(f: ConceptoFinalForm, def: CampoVisible): unknown {
  switch (def.tipo) {
    case "fecha": {
      const v = textoCampo(f, def.campo);
      return fechaValida(v) ? v : null;
    }
    case "entero":
      return entero(textoCampo(f, def.campo));
    case "decimal":
      return decimal(textoCampo(f, def.campo));
    case "si_no":
      return siNoCampo(f, def.campo);
  }
}

const vacio = (f: ConceptoFinalForm, def: CampoVisible) =>
  def.tipo === "si_no" ? siNoCampo(f, def.campo) === null : !textoCampo(f, def.campo).trim();

export function validarConceptoFinal(f: ConceptoFinalForm, campos: CamposConcepto): string | null {
  if (!f.archivo) return "Adjunte el concepto firmado (PDF)";
  if (!esPdf(f.archivo)) return "El concepto firmado debe ser PDF";
  return validarCamposConcepto(f, campos);
}

/** Valida los datos del concepto (sin el archivo): obligatorios con valor y formatos. */
export function validarCamposConcepto(f: ConceptoFinalForm, campos: CamposConcepto): string | null {
  for (const def of camposVisibles(campos)) {
    if (vacio(f, def)) {
      if (def.obligatorio) return `Complete: ${def.etiqueta}`;
      continue;
    }
    if (valorCampo(f, def) === null) return `Valor inválido: ${def.etiqueta}`;
  }
  return null;
}

/** Body de `.../version-final` del concepto: solo los campos del tipo con valor. */
export function bodyConceptoFinal(f: ConceptoFinalForm, campos: CamposConcepto, fileId: number): Record<string, unknown> {
  const body: Record<string, unknown> = { file_id: fileId };
  for (const def of camposVisibles(campos)) {
    const v = valorCampo(f, def);
    if (v !== null) body[def.campo] = v;
  }
  return body;
}
