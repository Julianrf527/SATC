import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, INFRACTION_ENDPOINTS, jsonBody } from "@shared/lib/api";
import type { Involucrado } from "@shared/types/involucrado";
import type { TipoNotificacion } from "@shared/types/sancionatorio";
import type { ExpedienteCompletoResponse, Quejoso } from "../types";
import { infraccionKeys } from "./queryKeys";

/**
 * Datos completos de un expediente (/expedientes/completo/{id}): dirección,
 * vereda, quejosos, recursos..., el tipo de notificación y las etapas que ya
 * existen. `staleTime: 0` conserva el comportamiento anterior (se volvía a
 * pedir cada vez que se abría el expediente) pero pinta la caché al instante.
 */
export function useExpedienteCompletoQuery(expedienteId: number | null | undefined) {
  return useQuery({
    queryKey: infraccionKeys.completo(expedienteId ?? 0),
    queryFn: () =>
      apiRequest<ExpedienteCompletoResponse>(
        INFRACTION_ENDPOINTS.INFRACTION_FUll(expedienteId as number),
      ),
    enabled: !!expedienteId,
    staleTime: 0,
  });
}

export type DatosBasicosPayload = {
  radicado: string;
  fecha_radicado: string;
  vereda_id: number;
  direccion: string;
  descripcion: string;
  tipos_afectacion_ids: number[];
  quejosos_ids: number[];
  recursos_ids: number[];
  radicados_asociados: string[];
};

/** PUT de los datos básicos (pestaña Información). */
export function useActualizarDatosBasicosMutation(expedienteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: DatosBasicosPayload) =>
      apiRequest(INFRACTION_ENDPOINTS.INFRACTION_BASIC_DATA(expedienteId), {
        method: "PUT",
        ...jsonBody(payload),
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: infraccionKeys.completo(expedienteId) }),
  });
}

export type NuevoQuejosoPayload = {
  nombre: string | null;
  telefono: string | null;
  correo: string | null;
  anonimo: boolean;
};

/** Crea un quejoso; devuelve el registro creado (o `null` si el backend no lo envía). */
export function useCrearQuejosoMutation() {
  return useMutation({
    mutationFn: async (payload: NuevoQuejosoPayload) => {
      const res = await apiRequest<{ data?: Quejoso | null }>(
        INFRACTION_ENDPOINTS.INFRACTION_CREATE_COMPLAINER,
        { method: "POST", ...jsonBody(payload) },
      );
      return res.data ?? null;
    },
  });
}

/** Archiva el expediente (cierre). Invalida todo lo cacheado del expediente. */
export function useArchivarExpedienteMutation(expedienteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiRequest(INFRACTION_ENDPOINTS.INFRACTION_ARCHIVE(expedienteId), { method: "PATCH" }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: infraccionKeys.expediente(expedienteId) }),
  });
}

/**
 * Involucrados vinculados al expediente (para los actos administrativos).
 * Antes se pedían en cada montaje y un fallo se ignoraba en silencio; se
 * mantiene: en error queda la lista vacía.
 */
export function useInvolucradosExpedienteQuery(expedienteId: number) {
  return useQuery({
    queryKey: infraccionKeys.involucrados(expedienteId),
    queryFn: async () => {
      const res = await apiRequest<{ data?: { involucrados?: Involucrado[] } }>(
        INFRACTION_ENDPOINTS.INFRACTION_INVOLVED_LIST(expedienteId),
      );
      return res.data?.involucrados ?? [];
    },
    enabled: !!expedienteId,
    staleTime: 0,
  });
}

/** Catálogo de tipos de notificación (personal, aviso...). */
export function useTiposNotificacionQuery() {
  return useQuery({
    queryKey: infraccionKeys.tiposNotificacion(),
    queryFn: async () => {
      const res = await apiRequest<{ data?: TipoNotificacion[] }>(
        INFRACTION_ENDPOINTS.INFRACTION_TIPO_NOTIFICACION,
      );
      return res.data ?? [];
    },
    staleTime: 5 * 60_000,
  });
}

/** Involucrados + tipos de notificación: lo que necesita `ActoAdmin` en cada etapa. */
export function useDatosActoAdmin(expedienteId: number) {
  const involucrados = useInvolucradosExpedienteQuery(expedienteId);
  const tipos = useTiposNotificacionQuery();
  return {
    involucrados: involucrados.data ?? [],
    tiposNotificacion: tipos.data ?? [],
  };
}
