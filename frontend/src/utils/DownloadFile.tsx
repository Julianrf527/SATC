import { apiCall, API_CONFIG } from "./api";

export async function downloadFile(
  versionId: number,
  fileName: string
): Promise<void> {
  try {
    const response = await apiCall(
      API_CONFIG.ENDPOINTS.DOCS_DOWNLOAD(versionId),
      {
        method: "GET",
      }
    );

    if (response.ok && response.blob) {
      // Crear URL temporal para el blob
      const url = window.URL.createObjectURL(response.blob);

      // Crear elemento <a> temporal para forzar descarga
      const link = document.createElement("a");
      link.href = url;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();

      // Limpiar
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } else {
      throw new Error("Error al descargar archivo");
    }
  } catch (error) {
    console.error("Error downloading file:", error);
    throw error;
  }
}
