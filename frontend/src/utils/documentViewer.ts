import { API_CONFIG, BASE_URL } from "./api";

/**
 * Open a document by its file ID in a new browser tab
 * @param fileId - The file ID from app-docs
 */
export function openDocumentById(fileId: number): void {
  const fullUrl = `${BASE_URL}${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD(fileId)}`;
  window.open(fullUrl, "_blank");
}

/**
 * Open a document by its URL path in a new browser tab
 * @param urlPath - The URL path to the document
 * @deprecated Use openDocumentById for new implementations
 */
export function openDocumentByUrl(urlPath: string): void {
  const fullUrl = `${BASE_URL}${urlPath}`;
  window.open(fullUrl, "_blank");
}

/**
 * Download a document by its file ID
 * @param fileId - The file ID from app-docs
 * @param filename - Optional filename for the download
 */
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

/**
 * Check if a document ID is valid (greater than 0)
 * @param documentId - The document ID to validate
 * @returns true if valid, false otherwise
 */
export function isValidDocumentId(
  documentId: number | null | undefined,
): documentId is number {
  return typeof documentId === "number" && documentId > 0;
}

/**
 * Generate a download URL for a document
 * @param fileId - The file ID from app-docs
 * @returns The complete download URL
 */
export function getDocumentUrl(fileId: number): string {
  return `${BASE_URL}${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD(fileId)}`;
}
