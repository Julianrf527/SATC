// Documento radicado por el usuario (`Radicado` de C.6–C.8: recurso, planos,
// subsanación, informes) y respuesta al requerimiento de la etapa 3 (C.5).
import { esPdf, fechaValida } from "./comunes";

export type RadicadoForm = { radicado: string; fecha_radicado: string; archivo: File | null };

export const RADICADO_VACIO: RadicadoForm = { radicado: "", fecha_radicado: "", archivo: null };

/** Máximo del backend para `radicado` / `radicado_oficio_entrada`. */
export const MAX_RADICADO = 15;

export function validarRadicado(f: RadicadoForm): string | null {
  const radicado = f.radicado.trim();
  if (!radicado) return "Indique el número de radicado";
  if (radicado.length > MAX_RADICADO) return `El radicado admite máximo ${MAX_RADICADO} caracteres`;
  if (!fechaValida(f.fecha_radicado)) return "Indique la fecha de radicado";
  if (!f.archivo) return "Adjunte el documento (PDF)";
  if (!esPdf(f.archivo)) return "El documento debe ser PDF";
  return null;
}

/** Body `Radicado` (POST que crea la fila, 201). */
export function bodyRadicado(f: RadicadoForm, fileId: number) {
  return { radicado: f.radicado.trim(), fecha_radicado: f.fecha_radicado, file_id: fileId };
}

/** Body de PUT `/requerimientos/etapa3/respuesta` (con `version` del nodo). */
export function bodyRespuestaRequerimiento(f: RadicadoForm, fileId: number, version: number) {
  return {
    version,
    radicado_oficio_entrada: f.radicado.trim(),
    fecha_oficio_entrada: f.fecha_radicado,
    doc_oficio_entrada_id: fileId,
  };
}
