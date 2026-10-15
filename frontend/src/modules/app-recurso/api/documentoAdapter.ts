import { apiRequest, RECURSO_ENDPOINTS } from "@shared/lib/api";
import type { ProcesoAdapter, ResultadoAccion } from "@features/proceso-revision";
import type { ProcesoDocumentoDetalle } from "../types";
import { recursoKeys } from "./queryKeys";
import { formRevision, formVersion } from "./revisionForms";

/** Respuesta de revisar / subir versión (B.1): estado y paso tras la acción. */
export type ResultadoDocumento = ResultadoAccion & {
  proceso_id?: number;
  paso_actual?: number;
  avanzo_paso?: boolean;
};

/**
 * Conecta el proceso de revisión de app-recurso (/recurso/revision-documentos)
 * con `@features/proceso-revision`, igual que `informeAdapter` de infraction.
 * El `id` es el **proceso_id** (Mis informes lo trae en `proceso_id`).
 */
export const documentoAdapter: ProcesoAdapter<ProcesoDocumentoDetalle> = {
  queryKey: (procesoId) => recursoKeys.proceso(procesoId),

  detalle: (procesoId) =>
    apiRequest<ProcesoDocumentoDetalle>(RECURSO_ENDPOINTS.RECURSO_REVISION_DETALLE(procesoId)),

  revisar: (procesoId, datos) =>
    apiRequest<ResultadoDocumento>(RECURSO_ENDPOINTS.RECURSO_REVISION_REVISAR(procesoId), {
      method: "POST",
      body: formRevision(datos),
    }),

  subirVersion: (procesoId, datos) =>
    apiRequest<ResultadoDocumento>(RECURSO_ENDPOINTS.RECURSO_REVISION_VERSIONES(procesoId), {
      method: "POST",
      body: formVersion(datos),
    }),

  urlVersion: (procesoId, version) =>
    RECURSO_ENDPOINTS.RECURSO_REVISION_DESCARGA_VERSION(procesoId, version.version_id),
  urlAdjunto: (procesoId, revision) => RECURSO_ENDPOINTS.RECURSO_REVISION_ADJUNTO(procesoId, revision.revision_id),
};
