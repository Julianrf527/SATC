import { BASE_URL } from "./api";
import { toastService } from "./toastService";

/**
 * Descarga un archivo binario (PDF unificado, etc.) desde un endpoint que
 * NO devuelve JSON. No usa apiCall porque apiCall siempre parsea la
 * respuesta como JSON/texto y no expone el blob.
 */
export async function downloadBlobFile(
  endpoint: string,
  filename: string
): Promise<{ ok: boolean; message?: string }> {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method: "GET",
    credentials: "include",
  });

  if (response.status === 401) {
    toastService.showToast({
      id: Date.now(),
      message: "Tu sesión ha expirado. Por favor, inicia sesión nuevamente.",
      type: "error",
    });
    document.cookie =
      "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    setTimeout(() => {
      window.location.href = "/login";
    }, 500);
    return { ok: false };
  }

  if (!response.ok) {
    let message = "No se pudo iniciar la descarga";
    try {
      const data = await response.json();
      message = data?.detail || message;
    } catch {
      // Ignorar parseo JSON fallido y usar mensaje por defecto
    }
    return { ok: false, message };
  }

  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objectUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(objectUrl);

  return { ok: true };
}
