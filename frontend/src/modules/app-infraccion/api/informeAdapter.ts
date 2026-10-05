import { apiRequest, INFRACTION_ENDPOINTS } from "@shared/lib/api";
import type { ProcesoAdapter, ProcesoDetalle, ResultadoAccion } from "@features/proceso-revision";
import type { ModoInforme } from "../types";
import { informeKeys } from "./informes";

/** `ProcesoDetalle` + datos del informe técnico (GET /revision-informes/...). */
export type ProcesoInformeDetalle = ProcesoDetalle & {
  informe_id: number;
  expediente_id: number;
  expediente_radicado: string | null;
  tipo_informe: string | null;
  modo: ModoInforme | null;
  activo: boolean;
  profesional_nombre: string | null;
  asignador_id: number | null;
};

/** Respuesta de revisar / subir versión: `informe_aceptado` si el proceso aprobó. */
export type ResultadoInforme = ResultadoAccion & {
  informe_id?: number;
  informe_aceptado?: boolean;
};

/**
 * Conecta el proceso de revisión propio del informe técnico
 * (/infraction/revision-informes) con features/proceso-revision. El `id` es
 * el **proceso_id** (los listados lo traen en `proceso_id`).
 */
export const informeAdapter: ProcesoAdapter<ProcesoInformeDetalle> = {
  queryKey: (procesoId) => informeKeys.proceso(procesoId),

  detalle: (procesoId) =>
    apiRequest<ProcesoInformeDetalle>(INFRACTION_ENDPOINTS.INFRACTION_REVISION_DETALLE(procesoId)),

  revisar: (procesoId, { accion, comentario, adjunto }) => {
    const form = new FormData();
    form.append("accion", accion);
    if (comentario) form.append("comentario", comentario);
    if (adjunto) form.append("adjunto", adjunto);
    return apiRequest<ResultadoInforme>(INFRACTION_ENDPOINTS.INFRACTION_REVISION_REVISAR(procesoId), {
      method: "POST",
      body: form,
    });
  },

  subirVersion: (procesoId, { archivo, comentario }) => {
    const form = new FormData();
    form.append("archivo", archivo);
    if (comentario) form.append("comentario", comentario);
    return apiRequest<ResultadoInforme>(INFRACTION_ENDPOINTS.INFRACTION_REVISION_VERSIONES(procesoId), {
      method: "POST",
      body: form,
    });
  },

  urlVersion: (procesoId, version) =>
    INFRACTION_ENDPOINTS.INFRACTION_REVISION_DESCARGA_VERSION(procesoId, version.version_id),
  urlAdjunto: (procesoId, revision) =>
    INFRACTION_ENDPOINTS.INFRACTION_REVISION_ADJUNTO(procesoId, revision.revision_id),
};
