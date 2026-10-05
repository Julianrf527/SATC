import { CheckCircle, FileSignature, XCircle, type LucideIcon } from "lucide-react";
import { BASE_URL } from "@shared/lib/api";
import type { EstadoTono } from "@shared/ui";

// Clases literales completas (Tailwind solo genera lo que encuentra escrito).
export const BOTON_TONO: Record<EstadoTono, string> = {
  info: "btn-info",
  success: "btn-success",
  warning: "btn-warning",
  error: "btn-error",
  neutral: "btn-neutral",
};

export const BORDE_TONO: Record<EstadoTono, string> = {
  info: "border-info bg-info/10 text-info",
  success: "border-success bg-success/10 text-success",
  warning: "border-warning bg-warning/10 text-warning",
  error: "border-error bg-error/10 text-error",
  neutral: "border-base-content/40 bg-base-200 text-base-content",
};

/**
 * Íconos semánticos de las acciones (`AccionDisponible.icono`). El backend
 * dice el significado; aquí solo se elige el dibujo. Desconocido = sin ícono.
 */
const ICONOS_ACCION: Record<string, LucideIcon> = {
  aprobar: CheckCircle,
  devolver: XCircle,
  firmar: FileSignature,
};

export const iconoAccion = (icono: string | null | undefined): LucideIcon | null =>
  (icono && ICONOS_ACCION[icono]) || null;

/** Abre la ruta de descarga en otra pestaña (la cookie de sesión viaja sola). */
export function abrirArchivo(ruta: string): void {
  window.open(`${BASE_URL}${ruta}`, "_blank", "noopener");
}

/** `".pdf,.docx"` para el atributo `accept` de un input file. */
export const acceptDe = (extensiones: string[]) => extensiones.join(",");

/** Extensión permitida según la lista que manda el backend (sin deducir nada). */
export function extensionPermitida(nombre: string, extensiones: string[]): boolean {
  const n = nombre.toLowerCase();
  return extensiones.length === 0 || extensiones.some((ext) => n.endsWith(ext.toLowerCase()));
}

export const listaExtensiones = (extensiones: string[]) =>
  extensiones.map((e) => e.replace(/^\./, "").toUpperCase()).join(", ");
