import { toastService } from "../toastService";

// window.ENV lo inyecta docker-entrypoint.sh en runtime (no es parte del build de Vite).
declare global {
  interface Window {
    ENV?: { VITE_API_URL?: string };
  }
}

const RESOLVED_BASE_URL: string =
  window.ENV?.VITE_API_URL ?? import.meta.env.VITE_API_URL ?? "";
export const BASE_URL: string = RESOLVED_BASE_URL || window.location.origin;


const showSessionExpiredToast = (message: string) => {
  toastService.showToast({
    id: Date.now(),
    message,
    type: "error",
  });
};

export const apiCall = async (
  endpoint: string,
  options: RequestInit = {},
  // Contrato heredado: devuelve el JSON sin tipar. El código nuevo usa `apiRequest<T>()`.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
): Promise<any> => {
  const headers: Record<string, string> = { ...options.headers } as Record<
    string,
    string
  >;

  // Con FormData el navegador debe fijar el Content-Type con su propio boundary.
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    credentials: "include",
    headers,
    ...options,
  });

  // Se intercepta antes del parseo genérico: el 401 dispara logout y redirección.
  if (response.status === 401) {
    const data = await response.json().catch(() => ({}));
    normalizeDetail(data);
    const yaEnLogin = window.location.pathname.startsWith("/login");

    document.cookie =
      "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";

    // Ya está viendo el login: recargar la misma página solo le tumba el
    // toast a medio mostrar sin aportar nada (no hay sesión que perder).
    if (!yaEnLogin) {
      if (data.detail === "session_replaced") {
        showSessionExpiredToast(
          "Tu sesión ha sido reemplazada por otro inicio de sesión. Si no fuiste tú, por favor cambia tu contraseña.",
        );
      } else {
        showSessionExpiredToast(
          "Tu sesión ha expirado. Por favor, inicia sesión nuevamente.",
        );
      }

      // Da tiempo a leer el toast antes de que el reload completo lo borre.
      setTimeout(() => {
        window.location.href = "/login";
      }, 2500);
    }

    return {
      ok: false,
      status: 401,
      unauthorized: true,
      ...data,
    };
  }

  // 403 se centraliza aquí para dar el mismo feedback en toda la app.
  if (response.status === 403) {
    const data = await response.json().catch(() => ({}));
    normalizeDetail(data);

    toastService.showToast({
      id: Date.now(),
      message:
        typeof data.detail === "string"
          ? data.detail
          : "No tienes permisos para realizar esta acción.",
      type: "error",
    });

    return {
      ok: false,
      status: 403,
      forbidden: true,
      ...data,
    };
  }

  // Evita falsos positivos cuando un proxy devuelve HTML (SPA fallback) con status 200.
  const contentType = response.headers.get("content-type") || "";
  if (response.status !== 204 && !contentType.includes("application/json")) {
    const raw = await response.text().catch(() => "");
    const detail =
      response.status === 503
        ? "Servicio temporalmente no disponible. Intente nuevamente."
        : response.status >= 500
          ? "Error interno del servidor. Intente nuevamente."
          : "Respuesta inesperada del servidor.";
    return {
      ok: false,
      status: response.status,
      detail,
      raw,
    };
  }

  const data = await response.json().catch(() => ({}));
  normalizeDetail(data);

  return {
    ok: response.ok,
    status: response.status,
    ...data,
  };
};

/**
 * Normaliza `data.detail` in-place a un string legible. FastAPI devuelve
 * errores de validación (422) como array de objetos Pydantic
 * ([{type, loc, msg, input}]) — sin esto, código que hace
 * `message: res.detail || "..."` termina mostrando ese JSON crudo en el
 * toast. Se aplica una sola vez acá para no depender de que cada uno de los
 * ~70 call sites recuerde envolverlo en formatApiErrorDetail.
 */
function normalizeDetail(data: Record<string, unknown>): void {
  if (data && "detail" in data && typeof data.detail !== "string") {
    data.detail = formatApiErrorDetail(data.detail, "Ocurrió un error inesperado.");
  }
}

/** Extrae un mensaje legible de un valor atrapado en catch (tipo unknown). */
export function getErrorMessage(e: unknown, fallback = "Error desconocido"): string {
  return e instanceof Error && e.message ? e.message : fallback;
}

/**
 * Formatea el campo `detail` de una respuesta de error de FastAPI: string
 * simple, o array de errores de validación de Pydantic ([{msg, loc, ...}]).
 */
export function formatApiErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((err) =>
        err && typeof err === "object" && "msg" in err
          ? String((err as { msg: unknown }).msg)
          : String(err),
      )
      .join(", ");
  }
  return fallback;
}

// ─────────────────────────────────────────────────────────────────────────────
// Capa para react-query
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Error tipado para respuestas `ok: false` de `apiCall`. `apiCall` NO lanza en
 * errores HTTP (devuelve `{ ok: false, status, detail }`); react-query necesita
 * que la promesa se rechace para poblar `error`/`isError`, así que los hooks de
 * datos usan `apiRequest`, que convierte esa respuesta en un `ApiError`.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly data: Record<string, unknown>;

  constructor(status: number, message: string, data: Record<string, unknown> = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

/**
 * Igual que `apiCall` (mismas cookies, manejo de 401/403 y toasts), pero lanza
 * `ApiError` si `ok` es false y devuelve el cuerpo tipado. Pensado para
 * `queryFn`/`mutationFn` de react-query.
 *
 *   const data = await apiRequest<{ usuarios: Usuario[] }>(ENDPOINT);
 */
export async function apiRequest<T = unknown>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await apiCall(endpoint, options);
  if (!res?.ok) {
    const detail =
      typeof res?.detail === "string" ? res.detail : "Ocurrió un error inesperado.";
    throw new ApiError(res?.status ?? 0, detail, res ?? {});
  }
  return res as T;
}

/** Helper para cuerpos JSON en mutaciones: `{ method: "POST", ...jsonBody(payload) }`. */
export const jsonBody = (payload: unknown): Pick<RequestInit, "body"> => ({
  body: JSON.stringify(payload),
});
