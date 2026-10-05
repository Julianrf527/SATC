import { ApiError } from "@shared/lib/api";

/**
 * `detail` que devolvió el backend, o `null` si no hubo (o si el error no es
 * HTTP). `apiRequest` rellena el mensaje con un genérico cuando falta
 * `detail`; con esto cada componente conserva su propio texto por defecto.
 */
export function detalleError(err: unknown): string | null {
  if (!(err instanceof ApiError)) return null;
  const detail = err.data?.detail;
  return typeof detail === "string" && detail ? detail : null;
}

/** El fetch falló sin respuesta HTTP (red caída, CORS...). */
export function esErrorDeConexion(err: unknown): boolean {
  return !(err instanceof ApiError);
}

/** Código HTTP del error, o `null` si no hubo respuesta. */
export function estadoError(err: unknown): number | null {
  return err instanceof ApiError ? err.status : null;
}
