// Formulario de documentos anexos (C.11): agregar y editar. Lógica pura.
import { esPdf } from "./comunes";

/**
 * Error del formulario o `null`. Al agregar el PDF es obligatorio; al editar
 * es opcional (solo si se reemplaza el actual), pero si viene debe ser PDF.
 */
export function validarAnexo(nombre: string, archivo: File | null, { editar = false } = {}): string | null {
  if (!nombre.trim()) return "Escriba el nombre del documento";
  if (!archivo) return editar ? null : "Adjunte el documento (PDF)";
  if (!esPdf(archivo)) return "El documento debe ser PDF";
  return null;
}

/** Body de `PUT /documentos-anexos/{id}`: `documento_anexo_id` solo si se reemplazó el PDF. */
export function bodyEditarAnexo(
  expedienteId: number,
  nombre: string,
  nuevoFileId?: number,
): { expediente_id: number; nombre: string; documento_anexo_id?: number } {
  return {
    expediente_id: expedienteId,
    nombre: nombre.trim(),
    ...(nuevoFileId ? { documento_anexo_id: nuevoFileId } : {}),
  };
}
