import { useMutation, useQuery, useQueryClient, type Query } from "@tanstack/react-query";
import { apiRequest, INFRACTION_ENDPOINTS } from "@shared/lib/api";
import type { ProcesoAdapter, ProcesoDetalle, ResultadoAccion } from "@features/proceso-revision";
import type { EtapaActoTipo, MisActuaciones } from "../types";
import { informeKeys } from "./informes";
import { infraccionKeys } from "./queryKeys";

/** Un paso de la cadena de revisión (como recurso): quién revisa y si ya lo hizo. */
export type PasoRevisionActo = {
  numero: number;
  estado: "completado" | "actual" | "pendiente";
  permisos: { permiso: string; etiqueta: string; revisado: boolean; revisor_nombre: string | null }[];
};

/** `ProcesoDetalle` + datos del acto y su etapa (GET /revision-actos/{id}). */
export type ProcesoActoDetalle = ProcesoDetalle & {
  paso_actual: number;
  total_pasos: number;
  pasos: PasoRevisionActo[];
  etapa_tipo: EtapaActoTipo;
  etapa_ref_id: number;
  tipo_documento: string;
  expediente_id: number;
  expediente_radicado: string | null;
  activo: boolean;
  encargado_id: number | null;
  encargado_nombre: string | null;
  acto_id: number | null;
  /** Soy el encargado actual y el acto está aprobado para firma. */
  puede_cargar_version_final: boolean;
};

/** GET /revision-actos/etapa/{tipo}/{id}: qué pintar en el panel del acto de la etapa. */
export type EstadoActoEtapa = {
  etapa_tipo: EtapaActoTipo;
  etapa_ref_id: number;
  expediente_id: number;
  acto_id: number | null;
  /** Abogado responsable actual del expediente (se muestra aunque no haya proceso). */
  encargado_id: number | null;
  encargado_nombre: string | null;
  es_encargado: boolean;
  puede_proyectar: boolean;
  puede_cargue_directo: boolean;
  proceso: ProcesoActoDetalle | null;
};

/** ¿El proceso espera algo de mí? (revisar, subir la corrección o cargar la versión final). */
export function requiereMiAccion(p: ProcesoActoDetalle): boolean {
  return p.acciones_disponibles.length > 0 || !!p.subida_version?.permitida || p.puede_cargar_version_final;
}

export const ETIQUETA_ETAPA_ACTO: Record<EtapaActoTipo, string> = {
  medida_preventiva: "Acto de la medida preventiva",
  etapa_concepto: "Acto de acoger concepto",
  etapa_cierre: "Acto de cierre",
};

export const actoKeys = {
  all: [...infraccionKeys.all, "actos-revision"] as const,
  etapa: (etapaTipo: EtapaActoTipo, refId: number) => [...actoKeys.all, "etapa", etapaTipo, refId] as const,
  proceso: (procesoId: number) => [...actoKeys.all, "proceso", procesoId] as const,
};

// El detalle lo refresca `useProcesoRevision` tras cada acción (ver informes.ts).
const noEsDetalleProceso = (q: Query) => q.queryKey[2] !== "proceso";
const esDeUnExpediente = (q: Query) => q.queryKey[1] === "expediente";

/**
 * Tras proyectar, revisar, subir versión o cargar la versión final: estado de
 * las etapas, Mis actuaciones y los datos de los expedientes (el acto creado
 * aparece en la etapa).
 */
export function useInvalidarActos() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: actoKeys.all, predicate: noEsDetalleProceso }),
      queryClient.invalidateQueries({ queryKey: informeKeys.misActuaciones() }),
      queryClient.invalidateQueries({ queryKey: infraccionKeys.all, predicate: esDeUnExpediente }),
    ]);
}

/**
 * Conecta /infraction/revision-actos con features/proceso-revision. El `id`
 * es el **proceso_id**.
 */
export const actoAdapter: ProcesoAdapter<ProcesoActoDetalle> = {
  queryKey: (procesoId) => actoKeys.proceso(procesoId),

  detalle: (procesoId) => apiRequest<ProcesoActoDetalle>(INFRACTION_ENDPOINTS.INFRACTION_ACTO_REV_DETALLE(procesoId)),

  revisar: (procesoId, { accion, comentario, adjunto }) => {
    const form = new FormData();
    form.append("accion", accion);
    if (comentario) form.append("comentario", comentario);
    if (adjunto) form.append("adjunto", adjunto);
    return apiRequest<ResultadoAccion>(INFRACTION_ENDPOINTS.INFRACTION_ACTO_REV_REVISAR(procesoId), {
      method: "POST",
      body: form,
    });
  },

  subirVersion: (procesoId, { archivo, comentario }) => {
    const form = new FormData();
    form.append("archivo", archivo);
    if (comentario) form.append("comentario", comentario);
    return apiRequest<ResultadoAccion>(INFRACTION_ENDPOINTS.INFRACTION_ACTO_REV_VERSIONES(procesoId), {
      method: "POST",
      body: form,
    });
  },

  urlVersion: (procesoId, version) =>
    INFRACTION_ENDPOINTS.INFRACTION_ACTO_REV_DESCARGA_VERSION(procesoId, version.version_id),
  urlAdjunto: (procesoId, revision) => INFRACTION_ENDPOINTS.INFRACTION_ACTO_REV_ADJUNTO(procesoId, revision.revision_id),
};

export function useEstadoActoEtapa(etapaTipo: EtapaActoTipo, refId: number | null | undefined) {
  return useQuery({
    queryKey: actoKeys.etapa(etapaTipo, refId ?? 0),
    enabled: !!refId,
    queryFn: () => apiRequest<EstadoActoEtapa>(INFRACTION_ENDPOINTS.INFRACTION_ACTO_REV_ETAPA(etapaTipo, refId!)),
  });
}

/**
 * Abre el proceso del acto en "pendiente de carga" (versión 0) para subir la
 * primera versión desde el modal del proceso, como recurso. Idempotente.
 */
export function useIniciarActoMutation() {
  const invalidar = useInvalidarActos();
  return useMutation({
    mutationFn: ({ etapaTipo, refId }: { etapaTipo: EtapaActoTipo; refId: number }) => {
      const form = new FormData();
      form.append("etapa_tipo", etapaTipo);
      form.append("etapa_ref_id", String(refId));
      return apiRequest<{ proceso_id: number; creado: boolean }>(INFRACTION_ENDPOINTS.INFRACTION_ACTO_REV_INICIAR, {
        method: "POST",
        body: form,
      });
    },
    onSuccess: () => invalidar(),
  });
}

export type VersionFinalActo = {
  archivo: File;
  tipoActo: "AUTO" | "RES";
  numerado: string;
  fechaNumerado: string;
  comentario?: string;
};

export function useVersionFinalActoMutation(procesoId: number) {
  const queryClient = useQueryClient();
  const invalidar = useInvalidarActos();
  return useMutation({
    mutationFn: ({ archivo, tipoActo, numerado, fechaNumerado, comentario }: VersionFinalActo) => {
      const form = new FormData();
      form.append("archivo", archivo);
      form.append("tipo_acto", tipoActo);
      form.append("numerado", numerado);
      form.append("fecha_numerado", fechaNumerado);
      if (comentario) form.append("comentario", comentario);
      return apiRequest<{ message?: string }>(INFRACTION_ENDPOINTS.INFRACTION_ACTO_REV_VERSION_FINAL(procesoId), {
        method: "POST",
        body: form,
      });
    },
    onSuccess: () => Promise.all([invalidar(), queryClient.invalidateQueries({ queryKey: actoKeys.proceso(procesoId) })]),
  });
}

// ── Mis actuaciones (informes + actos) ──────────────────────────────────────

const SIN_ACTUACIONES: MisActuaciones = {
  actuaciones: [],
  conteos: { total: 0, requieren_accion: 0 },
  filtros: { tipos_documento: [], estados: [], roles: [] },
};

export function useMisActuacionesQuery() {
  return useQuery({
    queryKey: informeKeys.misActuaciones(),
    queryFn: async () =>
      (await apiRequest<{ data?: MisActuaciones }>(INFRACTION_ENDPOINTS.INFRACTION_MIS_ACTUACIONES)).data ?? SIN_ACTUACIONES,
  });
}
