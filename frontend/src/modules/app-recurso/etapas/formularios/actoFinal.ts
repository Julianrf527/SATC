// "Cargar versión final" de un acto (C.1): PDF firmado + numerado + fecha,
// y los datos propios de algunas etapas (auto admite: técnico y fecha de
// visita; decisión: decisión y requiere memorias; recurso: resultado).
import type { ResultadoRecurso, TipoDecision } from "../../types";
import { type ClaseActo, esPdf, fechaValida, numeradoParaEnviar, numeradoValido } from "./comunes";

export type VarianteActoFinal = "simple" | "admite" | "decision" | "recurso";

export type ActoFinalForm = {
  archivo: File | null;
  clase_acto: ClaseActo | "";
  numerado: string;
  fecha_numerado: string;
  tecnico_id: number | "";
  fecha_visita_tecnica: string;
  decision: TipoDecision | "";
  /** Solo si la decisión es OTORGADA (V8). */
  requiere_memorias: boolean | null;
  resultado: ResultadoRecurso | "";
};

export const ACTO_FINAL_VACIO: ActoFinalForm = {
  archivo: null,
  clase_acto: "",
  numerado: "",
  fecha_numerado: "",
  tecnico_id: "",
  fecha_visita_tecnica: "",
  decision: "",
  requiere_memorias: null,
  resultado: "",
};

export const OPCIONES_DECISION: { value: TipoDecision; label: string }[] = [
  { value: "OTORGADA", label: "Otorgada" },
  { value: "NEGADA", label: "Negada" },
  { value: "DESISTIDA", label: "Desistida" },
];

export const OPCIONES_RESULTADO: { value: ResultadoRecurso; label: string }[] = [
  { value: "REPONE", label: "Repone" },
  { value: "CONFIRMA", label: "Confirma" },
  { value: "MODIFICA", label: "Modifica" },
  { value: "ADICIONA", label: "Adiciona" },
];

/** Primer error del formulario, o `null` si está completo. */
export function validarActoFinal(f: ActoFinalForm, variante: VarianteActoFinal): string | null {
  if (!f.archivo) return "Adjunte el acto firmado (PDF)";
  if (!esPdf(f.archivo)) return "El acto firmado debe ser PDF";
  if (!f.clase_acto) return "Seleccione el tipo de acto (AUTO o RES)";
  if (!numeradoValido(f.numerado)) return "El numerado debe ser un número de 1 a 4 dígitos";
  if (!fechaValida(f.fecha_numerado)) return "Indique la fecha de numerado";
  if (variante === "admite") {
    if (!f.tecnico_id) return "Seleccione el técnico encargado del concepto";
    if (!fechaValida(f.fecha_visita_tecnica)) return "Indique la fecha de visita técnica";
  }
  if (variante === "decision") {
    if (!f.decision) return "Seleccione la decisión";
    if (f.decision === "OTORGADA" && f.requiere_memorias === null) {
      return "Indique si la decisión exige memorias de cálculo (planos)";
    }
  }
  if (variante === "recurso" && !f.resultado) return "Seleccione el resultado del recurso";
  return null;
}

/** Body de `.../version-final` (`ActoFinal` + datos de la variante). */
export function bodyActoFinal(f: ActoFinalForm, variante: VarianteActoFinal, fileId: number): Record<string, unknown> {
  const body: Record<string, unknown> = {
    file_id: fileId,
    clase_acto: f.clase_acto,
    numerado: numeradoParaEnviar(f.numerado),
    fecha_numerado: f.fecha_numerado,
  };
  if (variante === "admite") {
    body.tecnico_id = f.tecnico_id;
    body.fecha_visita_tecnica = f.fecha_visita_tecnica;
  }
  if (variante === "decision") {
    body.decision = f.decision;
    // `requiere_memorias` solo aplica a OTORGADA (V8): en las demás no se envía.
    if (f.decision === "OTORGADA") body.requiere_memorias = f.requiere_memorias;
  }
  if (variante === "recurso") body.resultado = f.resultado;
  return body;
}
