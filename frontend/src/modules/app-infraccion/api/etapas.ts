import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, apiCall, apiRequest, INFRACTION_ENDPOINTS, jsonBody } from "@shared/lib/api";
import type {
  CierreEtapaData,
  ConceptoEtapaData,
  EtapaConsulta,
  MedidaPreventiva,
  RespuestaEtapa,
  TipoAcogidaConcepto,
  TipoMedida,
} from "../types";
import { infraccionKeys } from "./queryKeys";

// Las etapas devuelven 404 cuando todavía no existen: no es un error, es
// "etapa por crear" (y el cuerpo trae `creable`/`creable_msg`). Por eso se usa
// `apiCall` y se lanza `ApiError` solo para el resto de fallos.
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- cuerpo crudo de apiCall
async function consultarEtapa<T>(endpoint: string, extraer: (res: any) => T): Promise<EtapaConsulta<T>> {
  const res = await apiCall(endpoint, { method: "GET" });
  if (res?.status === 404) {
    return { data: null, creable: res.creable ?? false, creableMsg: res.creable_msg ?? null };
  }
  if (!res?.ok) {
    const detail = typeof res?.detail === "string" ? res.detail : "Ocurrió un error inesperado.";
    throw new ApiError(res?.status ?? 0, detail, res ?? {});
  }
  return { data: extraer(res), creable: true, creableMsg: null };
}

// staleTime 0: cada pestaña de etapa se volvía a consultar al abrirse; se
// mantiene, pero ahora con la caché pintada mientras llega la respuesta.
const ETAPA_QUERY_OPTIONS = { staleTime: 0 } as const;

// ── Respuesta + medida preventiva ─────────────────────────────────────────

export function useRespuestaEtapaQuery(expedienteId: number) {
  return useQuery({
    queryKey: infraccionKeys.respuesta(expedienteId),
    queryFn: () =>
      consultarEtapa<RespuestaEtapa>(
        INFRACTION_ENDPOINTS.INFRACTION_GET_ANSWER(expedienteId),
        (res) => ({
          respuesta: res.respuesta_data,
          medida: res.medida_preventiva?.ok ? (res.medida_preventiva.medida as MedidaPreventiva) : null,
        }),
      ),
    enabled: !!expedienteId,
    ...ETAPA_QUERY_OPTIONS,
  });
}

export type RespuestaPayload = {
  radicado: string;
  fecha_radicado: string;
  documento_radicado_id: number;
  requiere_medida_preventiva: boolean;
};

/** Crea (POST, `respuestaId` nulo) o actualiza (PUT) la etapa de respuesta. */
export function useGuardarRespuestaMutation(expedienteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ respuestaId, payload }: { respuestaId: number | null; payload: RespuestaPayload }) =>
      apiRequest(
        respuestaId === null
          ? INFRACTION_ENDPOINTS.INFRACTION_CREATE_ANSWER_STAGE(expedienteId)
          : INFRACTION_ENDPOINTS.INFRACTION_PUT_ANSWER(respuestaId),
        { method: respuestaId === null ? "POST" : "PUT", ...jsonBody(payload) },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: infraccionKeys.respuesta(expedienteId) }),
  });
}

export function useTiposMedidaQuery(enabled = true) {
  return useQuery({
    queryKey: infraccionKeys.tiposMedida(),
    queryFn: async () => {
      const res = await apiRequest<{ data?: TipoMedida[] }>(INFRACTION_ENDPOINTS.INFRACTION_TIPO_MEDIDA);
      return res.data ?? [];
    },
    enabled,
    staleTime: 5 * 60_000,
  });
}

export type MedidaPayload = {
  tipo_medida_id: number;
  cantidad: string;
  especie: string;
  estado_medida: boolean | null;
};

/** Crea (POST sobre la etapa de respuesta) o actualiza (PUT) la medida preventiva. */
export function useGuardarMedidaMutation(expedienteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      medidaId,
      etapaRespuestaId,
      payload,
    }: {
      medidaId: number | null;
      etapaRespuestaId: number | null;
      payload: MedidaPayload;
    }) =>
      apiRequest(
        medidaId !== null
          ? INFRACTION_ENDPOINTS.INFRACTION_UPDATE_MEDIDA(medidaId)
          : INFRACTION_ENDPOINTS.INFRACTION_CREATE_MEDIDA(etapaRespuestaId as number),
        { method: medidaId !== null ? "PUT" : "POST", ...jsonBody(payload) },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: infraccionKeys.respuesta(expedienteId) }),
  });
}

// ── Concepto ──────────────────────────────────────────────────────────────

export function useConceptoEtapaQuery(expedienteId: number) {
  return useQuery({
    queryKey: infraccionKeys.concepto(expedienteId),
    queryFn: () =>
      consultarEtapa<ConceptoEtapaData>(
        INFRACTION_ENDPOINTS.INFRACTION_GET_CONCEPTO(expedienteId),
        (res) => res.data as ConceptoEtapaData,
      ),
    enabled: !!expedienteId,
    ...ETAPA_QUERY_OPTIONS,
  });
}

export function useCrearConceptoMutation(expedienteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tipo: TipoAcogidaConcepto) =>
      apiRequest(INFRACTION_ENDPOINTS.INFRACTION_CREATE_CONCEPTO(expedienteId), {
        method: "POST",
        ...jsonBody({ tipo_acogida_concepto: tipo }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: infraccionKeys.concepto(expedienteId) }),
  });
}

export type ActualizarConceptoRespuesta = {
  message?: string;
  cierre_eliminado?: boolean;
};

/**
 * PUT del concepto: cambio de tipo de acogida y/o días de término. Cambiar el
 * tipo puede borrar el cierre, así que también se invalida esa etapa.
 */
export function useActualizarConceptoMutation(expedienteId: number, etapaConceptoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: { tipo_acogida_concepto: TipoAcogidaConcepto; dias_termino?: number }) =>
      apiRequest<ActualizarConceptoRespuesta>(
        INFRACTION_ENDPOINTS.INFRACTION_PUT_CONCEPTO(etapaConceptoId),
        { method: "PUT", ...jsonBody(payload) },
      ),
    onSuccess: () =>
      Promise.all([
        queryClient.invalidateQueries({ queryKey: infraccionKeys.concepto(expedienteId) }),
        queryClient.invalidateQueries({ queryKey: infraccionKeys.cierre(expedienteId) }),
      ]),
  });
}

export type OficioRemitePayload = {
  radicado: string;
  fecha_radicado: string;
  fecha_remitido: string;
  archivo_remite_id: number;
};

export function useGuardarOficioRemiteMutation(expedienteId: number, etapaConceptoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ oficioId, payload }: { oficioId: number | null; payload: OficioRemitePayload }) =>
      apiRequest(
        oficioId !== null
          ? INFRACTION_ENDPOINTS.INFRACTION_PUT_OFICIO_REMITE(oficioId)
          : INFRACTION_ENDPOINTS.INFRACTION_CREATE_OFICIO_REMITE(etapaConceptoId),
        { method: oficioId !== null ? "PUT" : "POST", ...jsonBody(payload) },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: infraccionKeys.concepto(expedienteId) }),
  });
}

export type SolicitudInformacionPayload = {
  radicado: string;
  fecha_radicado: string;
  archivo_solicitud_id: number;
};

export function useGuardarSolicitudInformacionMutation(expedienteId: number, etapaConceptoId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ solicitudId, payload }: { solicitudId: number | null; payload: SolicitudInformacionPayload }) =>
      apiRequest(
        solicitudId !== null
          ? INFRACTION_ENDPOINTS.INFRACTION_PUT_SOLICITUD_INFO(solicitudId)
          : INFRACTION_ENDPOINTS.INFRACTION_CREATE_SOLICITUD_INFO(etapaConceptoId),
        { method: solicitudId !== null ? "PUT" : "POST", ...jsonBody(payload) },
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: infraccionKeys.concepto(expedienteId) }),
  });
}

export function useEliminarSolicitudInformacionMutation(expedienteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (solicitudId: number) =>
      apiRequest(INFRACTION_ENDPOINTS.INFRACTION_DELETE_SOLICITUD_INFO(solicitudId), { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: infraccionKeys.concepto(expedienteId) }),
  });
}

// ── Cierre ────────────────────────────────────────────────────────────────

export function useCierreEtapaQuery(expedienteId: number) {
  return useQuery({
    queryKey: infraccionKeys.cierre(expedienteId),
    queryFn: () =>
      consultarEtapa<CierreEtapaData>(
        INFRACTION_ENDPOINTS.INFRACTION_GET_CIERRE(expedienteId),
        (res) => res.data as CierreEtapaData,
      ),
    enabled: !!expedienteId,
    ...ETAPA_QUERY_OPTIONS,
  });
}

export function useCrearCierreMutation(expedienteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiRequest(INFRACTION_ENDPOINTS.INFRACTION_CREATE_CIERRE(expedienteId), { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: infraccionKeys.cierre(expedienteId) }),
  });
}
