import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, INFRACTION_ENDPOINTS, jsonBody } from "@shared/lib/api";
import { generateDocumentFileName, uploadFileToDocuments } from "@shared/lib/fileUpload";
import type { Involucrado } from "@shared/types/involucrado";
import type { TipoNotificacion } from "@shared/types/sancionatorio";
import type { ExpedienteCompletoResponse, Quejoso } from "../types";
import { infraccionKeys } from "./queryKeys";
import { invalidarExpediente } from "./invalidar";

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
    onSuccess: () => invalidarExpediente(queryClient, expedienteId),
  });
}

/**
 * Adjunta o reemplaza el PDF "Radicado inicial": lo sube a app-docs y fija su
 * `file_id` en el expediente (el backend valida que sea PDF y mueve los
 * contadores de uso). La validación de tipo/tamaño la hace el formulario.
 */
export function useFijarRadicadoInicialMutation(expedienteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ archivo, radicado }: { archivo: File; radicado: string }) => {
      const hoy = new Date().toISOString().split("T")[0];
      const fileId = await uploadFileToDocuments(
        archivo,
        generateDocumentFileName("RADICADO_INICIAL", radicado, hoy),
      );
      return apiRequest(INFRACTION_ENDPOINTS.INFRACTION_RADICADO_INICIAL(expedienteId), {
        method: "PUT",
        ...jsonBody({ file_id: fileId }),
      });
    },
    onSuccess: () => invalidarExpediente(queryClient, expedienteId),
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
    onSuccess: () => invalidarExpediente(queryClient, expedienteId),
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
