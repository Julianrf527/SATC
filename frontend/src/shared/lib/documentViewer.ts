import { API_CONFIG, BASE_URL } from "./api";

export function openDocumentById(fileId: number): void {
  const fullUrl = `${BASE_URL}${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD(fileId)}`;
  window.open(fullUrl, "_blank");
}

/** @deprecated Usar openDocumentById: la ruta se arma desde el file ID. */
export function openDocumentByUrl(urlPath: string): void {
  const fullUrl = `${BASE_URL}${urlPath}`;
  window.open(fullUrl, "_blank");
}

export function downloadDocumentById(fileId: number, filename?: string): void {
  const link = document.createElement("a");
  link.href = `${BASE_URL}${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD(fileId)}`;
  if (filename) {
    link.download = filename;
  }
  link.target = "_blank";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export function isValidDocumentId(
  documentId: number | null | undefined,
): documentId is number {
  return typeof documentId === "number" && documentId > 0;
}

export function getDocumentUrl(fileId: number): string {
  return `${BASE_URL}${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD(fileId)}`;
}
