import { keepPreviousData, useMutation, useQuery, useQueryClient, type Query } from "@tanstack/react-query";
import { ApiError, apiCall, apiRequest, INFRACTION_ENDPOINTS, jsonBody } from "@shared/lib/api";
import type {
  EtapaConsulta,
  FilaRecursoAfectado,
  ImpactoCambioModo,
  InformeTecnico,
  MiInforme,
  ModoInforme,
  ProfesionalDisponible,
  TipoInforme,
} from "../types";
import { invalidarExpediente } from "./invalidar";
import { infraccionKeys } from "./queryKeys";

// ── Claves ──────────────────────────────────────────────────────────────────
// Todo lo de informes cuelga de `informeKeys.all`, salvo la etapa del
// expediente, que va bajo `infraccionKeys.expediente(id)` para refrescarse
// junto con el resto de etapas.
export const informeKeys = {
  all: [...infraccionKeys.all, "informes"] as const,
  listas: () => [...informeKeys.all, "lista"] as const,
  lista: (filtros: FiltrosInformes, page: number) => [...informeKeys.listas(), filtros, page] as const,
  mios: () => [...informeKeys.all, "mios"] as const,
  disponibles: () => [...informeKeys.all, "disponibles"] as const,
  proceso: (procesoId: number) => [...informeKeys.all, "proceso", procesoId] as const,
  recursos: (informeId: number) => [...informeKeys.all, "recursos", informeId] as const,
  impactoCambioModo: (informeId: number) => [...informeKeys.all, "impacto-cambio-modo", informeId] as const,
  etapa: (expedienteId: number, tipo: TipoInforme) =>
    [...infraccionKeys.expediente(expedienteId), "etapa", "informe", tipo] as const,
};

// Cualquier consulta bajo `infraccionKeys.expediente(id)`: etapas de informe
// y también `completo` (última etapa y estado dependen de los informes).
const esDeUnExpediente = (q: Query) => q.queryKey[1] === "expediente";

/**
 * Invalida listados, matrices, las etapas de informe (Visita / Seguimiento),
 * los datos de los expedientes y sus listados (última etapa y estado). Se usa
 * tras asignar, revisar, subir versión, cargue manual... Como muchas de esas
 * acciones no saben de qué expediente es el informe, se invalida el subárbol
 * de todos (solo se vuelven a pedir los que están en pantalla).
 */
// El detalle de un proceso ya lo refresca `useProcesoRevision` tras cada
// acción: invalidarlo aquí también cancelaba y repetía esa misma petición.
const noEsDetalleProceso = (q: Query) => q.queryKey[2] !== "proceso";

export function useInvalidarInformes() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: informeKeys.all, predicate: noEsDetalleProceso }),
      queryClient.invalidateQueries({ queryKey: infraccionKeys.all, predicate: esDeUnExpediente }),
      queryClient.invalidateQueries({ queryKey: infraccionKeys.listaExpedientes() }),
    ]);
}

// ── Listado de gestión (/informes) ─────────────────────────────────────────

export type FiltrosInformes = {
  fechaDesde: string;
  fechaHasta: string;
  aceptado: "" | "true" | "false";
  profesionalId: number | "";
  radicado: string;
  tipo: string;
};

export const LIMIT_INFORMES = 20;

export type ListaInformes = {
  data: InformeTecnico[];
  total: number;
  total_pages: number;
  profesionales_disponibles: ProfesionalDisponible[];
  revisores_disponibles: ProfesionalDisponible[];
};

export function useInformesQuery(filtros: FiltrosInformes, page: number) {
  return useQuery({
    queryKey: informeKeys.lista(filtros, page),
    placeholderData: keepPreviousData,
    queryFn: async (): Promise<ListaInformes> => {
      const p = new URLSearchParams({ page: String(page), limit: String(LIMIT_INFORMES) });
      if (filtros.fechaDesde) p.append("fecha_desde", filtros.fechaDesde);
      if (filtros.fechaHasta) p.append("fecha_hasta", filtros.fechaHasta);
      if (filtros.aceptado) p.append("aceptado", filtros.aceptado);
      if (filtros.profesionalId !== "") p.append("profesional_id", String(filtros.profesionalId));
      if (filtros.radicado.trim()) p.append("expediente_radicado", filtros.radicado.trim());
      if (filtros.tipo) p.append("tipo_informe", filtros.tipo);
      const res = await apiRequest<Partial<ListaInformes>>(
        `${INFRACTION_ENDPOINTS.INFRACTION_REPORTS_LIST}?${p.toString()}`,
      );
      return {
        data: res.data ?? [],
        total: res.total ?? 0,
        total_pages: res.total_pages ?? 1,
        profesionales_disponibles: res.profesionales_disponibles ?? [],
        revisores_disponibles: res.revisores_disponibles ?? [],
      };
    },
  });
}

export type AsignacionInforme = {
  profesional_id: number;
  revisor_id: number;
  fecha_programacion_visita?: string;
};

/**
 * POST = asignar (crea el proceso; si el vigente quedó finalizado lo archiva).
 * PUT = reasignar (cierra el vigente y crea uno nuevo). El POST responde 409
 * si hay un proceso vigente sin terminar: el componente ofrece reasignar.
 */
export function useAsignarInformeMutation() {
  const invalidar = useInvalidarInformes();
  return useMutation({
    mutationFn: ({ informeId, reasignar, datos }: { informeId: number; reasignar: boolean; datos: AsignacionInforme }) =>
      apiRequest<{ proceso_id: number; message?: string }>(INFRACTION_ENDPOINTS.INFRACTION_REPORTS_ASIGNAR(informeId), {
        method: reasignar ? "PUT" : "POST",
        ...jsonBody(datos),
      }),
    onSuccess: invalidar,
  });
}

// ── Mis informes (/informes/mios) ───────────────────────────────────────────

export function useMisInformesQuery() {
  return useQuery({
    queryKey: informeKeys.mios(),
    queryFn: async () => (await apiRequest<{ data?: MiInforme[] }>(INFRACTION_ENDPOINTS.INFRACTION_MIS_INFORMES)).data ?? [],
  });
}

// ── Etapa del expediente (Visita / Seguimiento) ─────────────────────────────

/** 404 = la etapa aún no existe (el cuerpo trae `creable`/`creable_msg`). */
export function useInformeEtapaQuery(expedienteId: number, tipo: TipoInforme) {
  return useQuery({
    queryKey: informeKeys.etapa(expedienteId, tipo),
    enabled: !!expedienteId,
    staleTime: 0,
    queryFn: async (): Promise<EtapaConsulta<InformeTecnico>> => {
      const res = await apiCall(INFRACTION_ENDPOINTS.INFRACTION_GET_REPORT(expedienteId, tipo));
      if (res?.status === 404) {
        return { data: null, creable: res.creable ?? false, creableMsg: res.creable_msg ?? null };
      }
      if (!res?.ok) {
        throw new ApiError(res?.status ?? 0, typeof res?.detail === "string" ? res.detail : "Error al cargar el informe", res ?? {});
      }
      return { data: res.data as InformeTecnico, creable: false, creableMsg: null };
    },
  });
}

export function useCrearInformeEtapaMutation(expedienteId: number, tipo: TipoInforme) {
  const invalidar = useInvalidarInformes();
  return useMutation({
    mutationFn: () =>
      apiRequest(INFRACTION_ENDPOINTS.INFRACTION_CREATE_REPORT(expedienteId, tipo), { method: "POST" }),
    onSuccess: invalidar,
  });
}

// ── Modo de cargue y cargue manual ──────────────────────────────────────────

export function useDisponiblesQuery(enabled: boolean) {
  return useQuery({
    queryKey: informeKeys.disponibles(),
    enabled,
    queryFn: async () => {
      const res = await apiRequest<{
        profesionales_disponibles?: ProfesionalDisponible[];
        revisores_disponibles?: ProfesionalDisponible[];
      }>(INFRACTION_ENDPOINTS.INFRACTION_REPORTS_DISPONIBLES);
      return { profesionales: res.profesionales_disponibles ?? [], revisores: res.revisores_disponibles ?? [] };
    },
  });
}

/**
 * Vista previa del cambio de modo: etapas posteriores del expediente que se
 * borrarían en cascada (visita → concepto, seguimiento y cierre; seguimiento
 * → cierre). Se pide al abrir la confirmación y siempre fresca.
 */
export function useImpactoCambioModoQuery(informeId: number, enabled: boolean) {
  return useQuery({
    queryKey: informeKeys.impactoCambioModo(informeId),
    enabled,
    staleTime: 0,
    gcTime: 0,
    queryFn: async () =>
      (await apiRequest<Partial<ImpactoCambioModo>>(INFRACTION_ENDPOINTS.INFRACTION_REPORTS_CAMBIAR_MODO_IMPACTO(informeId)))
        .etapas ?? [],
  });
}

/** Cambiar el modo puede borrar etapas posteriores: se invalida todo el expediente además de los informes. */
export function useCambiarModoMutation(informeId: number, expedienteId: number) {
  const queryClient = useQueryClient();
  const invalidar = useInvalidarInformes();
  return useMutation({
    mutationFn: (modo: ModoInforme) =>
      apiRequest<{ message?: string; etapas_eliminadas?: ImpactoCambioModo["etapas"] }>(
        INFRACTION_ENDPOINTS.INFRACTION_REPORTS_CAMBIAR_MODO(informeId),
        { method: "PUT", ...jsonBody({ modo }) },
      ),
    onSuccess: () => Promise.all([invalidar(), invalidarExpediente(queryClient, expedienteId)]),
  });
}

export type CargueManualDatos = {
  file_id: number;
  fecha_recibido: string;
  fecha_aceptacion: string;
  fecha_programacion_visita?: string;
  profesional_id?: number;
  revisor_id?: number;
};

export function useCargueManualMutation(informeId: number) {
  const invalidar = useInvalidarInformes();
  return useMutation({
    mutationFn: (datos: CargueManualDatos) =>
      apiRequest(INFRACTION_ENDPOINTS.INFRACTION_REPORTS_CARGUE_MANUAL(informeId), {
        method: "POST",
        ...jsonBody(datos),
      }),
    onSuccess: invalidar,
  });
}

// ── Matriz de recursos afectados ────────────────────────────────────────────

export function useMatrizRecursosQuery(informeId: number, enabled = true) {
  return useQuery({
    queryKey: informeKeys.recursos(informeId),
    enabled,
    staleTime: 0,
    queryFn: async () =>
      (await apiRequest<{ data?: FilaRecursoAfectado[] }>(INFRACTION_ENDPOINTS.INFRACTION_INFORME_RECURSOS(informeId))).data ?? [],
  });
}

export function useGuardarMatrizMutation(informeId: number) {
  const invalidar = useInvalidarInformes();
  return useMutation({
    mutationFn: (filas: FilaRecursoAfectado[]) =>
      apiRequest(INFRACTION_ENDPOINTS.INFRACTION_INFORME_RECURSOS(informeId), {
        method: "PUT",
        ...jsonBody({ filas }),
      }),
    onSuccess: invalidar,
  });
}
