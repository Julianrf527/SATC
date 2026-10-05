import { apiRequest, DOCUMENTS_ENDPOINTS } from "@shared/lib/api";
import type { ProcesoAdapter, ProcesoDetalle, ResultadoAccion } from "@features/proceso-revision";
import { documentosKeys } from "./queryKeys";

/**
 * Conecta el flujo genérico de app-docs (/documents/docs/...) con
 * features/proceso-revision. Campos multipart comunes a todos los flujos:
 * revisar = `accion`, `comentario`, `adjunto`; subir versión = `archivo`, `comentario`.
 */
export const docsAdapter: ProcesoAdapter<ProcesoDetalle> = {
  queryKey: (id) => documentosKeys.detalle(id),

  // GET /detail ya devuelve el contrato ProcesoDetalle (sin `ok`).
  detalle: (id) => apiRequest<ProcesoDetalle>(DOCUMENTS_ENDPOINTS.DOCS_DETAIL(id)),

  revisar: (id, { accion, comentario, adjunto }) => {
    const form = new FormData();
    form.append("accion", accion);
    if (comentario) form.append("comentario", comentario);
    if (adjunto) form.append("adjunto", adjunto);
    return apiRequest<ResultadoAccion>(DOCUMENTS_ENDPOINTS.DOCS_REVIEW(id), {
      method: "POST",
      body: form,
    });
  },

  subirVersion: (id, { archivo, comentario }) => {
    const form = new FormData();
    form.append("archivo", archivo);
    if (comentario) form.append("comentario", comentario);
    return apiRequest<ResultadoAccion>(DOCUMENTS_ENDPOINTS.DOCS_UPLOAD_VERSION(id), {
      method: "POST",
      body: form,
    });
  },

  urlVersion: (_id, version) => DOCUMENTS_ENDPOINTS.DOCS_DOWNLOAD(version.version_id),
  urlAdjunto: (_id, revision) => DOCUMENTS_ENDPOINTS.DOCS_DOWNLOAD_REVISION(revision.revision_id),
};
