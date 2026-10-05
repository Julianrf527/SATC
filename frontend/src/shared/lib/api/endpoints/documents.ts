// Endpoints del servicio app-docs (/documents).
// Strings fijos o funciones que construyen la ruta; se concatenan a BASE_URL en apiCall.
export const DOCUMENTS_ENDPOINTS = {
  // docs route: flujo genérico de revisión de documentos (contrato ProcesoDetalle)
  DOCS_LIST: "/documents/docs/list",
  DOCS_DETAIL: (documentId: number) => `/documents/docs/detail/${documentId}`,
  DOCS_CREATE: "/documents/docs/create",
  DOCS_UPLOAD_VERSION: (documentId: number) =>
    `/documents/docs/upload-version/${documentId}`,
  DOCS_REVIEW: (documentId: number) => `/documents/docs/review/${documentId}`,
  DOCS_DOWNLOAD: (versionId: number) =>
    `/documents/docs/download/${versionId}`,
  DOCS_DOWNLOAD_REVISION: (revisionId: number) =>
    `/documents/docs/download-revision/${revisionId}`,
  DOCS_STATS: "/documents/docs/stats",
  DOCS_REVIEWERS: "/documents/docs/reviewers",
  // files route
  FILE_UPLOAD: "/documents/files/upload",
  FILE: (file_id: number) => `/documents/files/${file_id}`,
  FILE_BATCH: "/documents/files/batch",
  FILE_DOWNLOAD: (file_id: number) => `/documents/files/download/${file_id}`,
};
