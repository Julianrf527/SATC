import { ApiError } from "@shared/lib/api";

/**
 * Mensaje para un error de mutación/consulta del módulo. Conserva la regla
 * que tenían los componentes con `apiCall`: si el servidor respondió con un
 * `detail` se muestra ese; si respondió sin él, `fallback`; si ni siquiera hubo
 * respuesta (red), `fallbackRed`.
 */
export function apiErrorMessage(
  error: unknown,
  fallback: string,
  fallbackRed: string = fallback,
): string {
  if (error instanceof ApiError) {
    const detail = error.data?.detail;
    return typeof detail === "string" && detail ? detail : fallback;
  }
  return fallbackRed;
}
