import { ApiError } from "@shared/lib/api";

/** Mensaje que muestra la UI ante un 409 de bloqueo optimista (API.md A). */
export const MENSAJE_CONFLICTO = "Fue modificado por otra persona, recarga";

/** `detail` del backend, o `null` si no hubo (o si el error no es HTTP). */
export function detalleError(err: unknown): string | null {
  if (!(err instanceof ApiError)) return null;
  const detail = err.data?.detail;
  return typeof detail === "string" && detail ? detail : null;
}

/** Código HTTP del error, o `null` si no hubo respuesta. */
export function estadoError(err: unknown): number | null {
  return err instanceof ApiError ? err.status : null;
}

/** Texto para el usuario: el `detail` del backend o el genérico dado. */
export function mensajeError(err: unknown, fallback: string): string {
  return detalleError(err) ?? fallback;
}

/**
 * Mensaje de una escritura de etapa: ante 409 el `detail` del backend ("Ya fue
 * asignado", numerado repetido...) o el aviso de conflicto; si falló la subida
 * del PDF a app-docs, su mensaje.
 */
export function mensajeEscritura(err: unknown, fallback: string): string {
  if (estadoError(err) === 409) return detalleError(err) ?? MENSAJE_CONFLICTO;
  if (err instanceof ApiError) return detalleError(err) ?? fallback;
  return err instanceof Error && err.message ? err.message : fallback;
}
