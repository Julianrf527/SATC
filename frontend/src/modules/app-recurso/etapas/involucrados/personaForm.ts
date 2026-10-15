import type { PersonaForm } from "../../api/personaForm";
import type { PersonaInvolucrada } from "../../types";

/** Documento listo para buscar en app-involved (mismo criterio que infraction). */
export function documentoBuscable(f: PersonaForm): boolean {
  if (f.numero_documento.trim().length < 7) return false;
  return f.tipo_documento !== "NIT" || f.digito_verificacion.trim() !== "";
}

/**
 * Valida una persona antes de vincularla. Si ya existe en app-involved
 * basta con encontrarla; si no, se necesitan los datos para crearla.
 */
export function validarPersona(f: PersonaForm, existente: PersonaInvolucrada | null, quien: string): string | null {
  if (existente) return null;
  if (!f.numero_documento.trim()) return `Ingrese el documento del ${quien}`;
  if (f.numero_documento.trim().length < 7) return `El documento del ${quien} debe tener al menos 7 dígitos`;
  if (f.tipo_documento === "NIT" && !f.digito_verificacion.trim()) return `Ingrese el dígito de verificación del ${quien}`;
  if (!f.nombre.trim()) return `Ingrese el nombre del ${quien}`;
  return null;
}

/** Datos de la persona encontrada → formulario (campos bloqueados en la vista). */
export function formDesdePersona(p: PersonaInvolucrada): PersonaForm {
  return {
    tipo_documento: p.tipo_documento ?? "CC",
    numero_documento: p.numero_documento != null ? String(p.numero_documento) : "",
    digito_verificacion: p.digito_verificacion ?? "",
    nombre: p.nombre ?? "",
    celular: p.celular != null ? String(p.celular) : "",
    correo: p.correo ?? "",
    direccion: p.direccion ?? "",
  };
}

/** Nombre a mostrar aunque app-involved no haya respondido (`{ id }`). */
export function nombrePersona(p: PersonaInvolucrada | null | undefined): string {
  if (!p) return "—";
  return p.nombre?.trim() || `Persona #${p.id}`;
}

/** "CC 1020304050" / "NIT 900123456-3". */
export function documentoPersona(p: PersonaInvolucrada | null | undefined): string {
  if (!p || p.numero_documento == null) return "";
  const dv = p.digito_verificacion ? `-${p.digito_verificacion}` : "";
  return `${p.tipo_documento ?? ""} ${p.numero_documento}${dv}`.trim();
}
