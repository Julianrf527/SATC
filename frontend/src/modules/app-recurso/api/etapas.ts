import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, jsonBody, RECURSO_ENDPOINTS } from "@shared/lib/api";
import { uploadFileToDocuments } from "@shared/lib/fileUpload";
import type { ConceptoParaTecnico, TecnicoRecurso } from "../types";
import { estadoError } from "./errors";
import { invalidarExpediente } from "./invalidar";
import { recursoKeys } from "./queryKeys";

/** Petición de escritura de una etapa (sección C). */
export type PeticionEtapa = {
  url: string;
  method: "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
};

/** Respuesta de escritura de C: `{ ok, message, data: {id, version, proceso_id?, acto_id?} }`. */
export type RespuestaEtapa = {
  message?: string;
  data?: { id?: number; version?: number | null; proceso_id?: number; acto_id?: number | null };
};

export type EscrituraEtapa = {
  /**
   * PDFs que se suben antes a app-docs (como infraction). La clave se usa en
   * `peticion` para leer su `file_id`; los `null` se omiten.
   */
  archivos?: Record<string, File | null | undefined>;
  /** Arma la petición con los `file_id` subidos. */
  peticion: (fileIds: Record<string, number>) => PeticionEtapa;
};

/** Nombre del archivo en app-docs: `<CLAVE>_<expediente>_<fecha>.pdf`. */
function nombreArchivo(clave: string, expedienteId: number, archivo: File): string {
  const hoy = new Date().toISOString().split("T")[0].replace(/-/g, "");
  const ext = archivo.name.includes(".") ? archivo.name.split(".").pop() : "pdf";
  return `${clave.toUpperCase()}_${expedienteId}_${hoy}.${ext}`;
}

async function subirArchivos(expedienteId: number, archivos: EscrituraEtapa["archivos"]) {
  const ids: Record<string, number> = {};
  for (const [clave, archivo] of Object.entries(archivos ?? {})) {
    if (archivo) ids[clave] = await uploadFileToDocuments(archivo, nombreArchivo(clave, expedienteId, archivo));
  }
  return ids;
}

/**
 * Toda escritura de etapas (asignarme, versión final, documentos, radicados,
 * técnico, anexos, terceros, super gestión): sube los PDF, envía la petición
 * y recarga el árbol (GET /expedientes/{id}) y Mis informes. Ante 409
 * (versión vieja, ya asignado...) también recarga.
 */
export function useEscrituraEtapaMutation(expedienteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ archivos, peticion }: EscrituraEtapa) => {
      const ids = await subirArchivos(expedienteId, archivos);
      const { url, method, body } = peticion(ids);
      return apiRequest<RespuestaEtapa>(url, { method, ...(body !== undefined ? jsonBody(body) : {}) });
    },
    onSuccess: () =>
      Promise.all([
        invalidarExpediente(queryClient, expedienteId),
        queryClient.invalidateQueries({ queryKey: recursoKeys.misDocumentos() }),
      ]),
    onError: (err) => {
      if (estadoError(err) === 409) void invalidarExpediente(queryClient, expedienteId);
    },
  });
}

/** Técnicos seleccionables (usuarios con `recurso_tecnico`, C.4). Solo gestión. */
export function useTecnicosQuery(enabled = true) {
  return useQuery({
    queryKey: recursoKeys.tecnicos(),
    queryFn: async () =>
      (await apiRequest<{ data?: TecnicoRecurso[] }>(RECURSO_ENDPOINTS.RECURSO_ETAPAS_TECNICOS)).data ?? [],
    enabled,
    staleTime: 5 * 60_000,
  });
}

/** Abogados seleccionables como encargado en el cargue directo (usuarios con `recurso_gestionar`, C.9). */
export function useAbogadosQuery(enabled = true) {
  return useQuery({
    queryKey: recursoKeys.abogados(),
    queryFn: async () =>
      (await apiRequest<{ data?: TecnicoRecurso[] }>(RECURSO_ENDPOINTS.RECURSO_ETAPAS_ABOGADOS)).data ?? [],
    enabled,
    staleTime: 5 * 60_000,
  });
}

/** GET /etapas/conceptos/{id}: concepto del técnico desde Mis informes (C.4). */
export function useConceptoTecnicoQuery(conceptoId: number | null) {
  return useQuery({
    queryKey: recursoKeys.concepto(conceptoId ?? 0),
    queryFn: async () =>
      (await apiRequest<{ data: ConceptoParaTecnico }>(RECURSO_ENDPOINTS.RECURSO_CONCEPTO(conceptoId as number))).data,
    enabled: !!conceptoId,
    staleTime: 0,
  });
}

/**
 * POST /etapas/conceptos/{id}/version-final (técnico, desde Mis informes).
 * Sube el PDF firmado y recarga Mis informes y el concepto.
 */
export function useVersionFinalConceptoMutation(conceptoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ archivo, body }: { archivo: File; body: (fileId: number) => Record<string, unknown> }) => {
      const fileId = await uploadFileToDocuments(archivo, nombreArchivo("CONCEPTO", conceptoId, archivo));
      return apiRequest<RespuestaEtapa>(RECURSO_ENDPOINTS.RECURSO_CONCEPTO_VERSION_FINAL(conceptoId), {
        method: "POST",
        ...jsonBody(body(fileId)),
      });
    },
    onSettled: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: recursoKeys.misDocumentos() }),
        queryClient.invalidateQueries({ queryKey: recursoKeys.concepto(conceptoId) }),
      ]),
  });
}
