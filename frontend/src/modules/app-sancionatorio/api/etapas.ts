import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  apiRequest,
  ApiError,
  INFRACTION_ENDPOINTS,
  SANCTIONING_ENDPOINTS as EP,
} from "@shared/lib/api";
import type { Creable, EtapaRespuesta, MigracionMedida, TipoCatalogo } from "../types";
import { sancionatorioKeys } from "./queryKeys";

/**
 * Endpoints de cada etapa del proceso sancionatorio. `respuestaKey` es la
 * propiedad del JSON del GET que trae los datos de la etapa.
 */
export const ETAPAS_API = {
  indagacion: { get: EP.FILE_INVESTIGATION, create: EP.FILE_INVESTIGATION_CREATE, respuestaKey: "indagacion" },
  medida: { get: EP.FILE_MEASURE, create: EP.FILE_MEASURE_CREATE, respuestaKey: "medida" },
  inicio: { get: EP.FILE_START_PROCESS, create: EP.FILE_START_PROCESS_CREATE, respuestaKey: "inicio_proceso" },
  cesacion: { get: EP.FILE_CESSATION, create: EP.FILE_CESSATION_CREATE, respuestaKey: "cesacion" },
  formulacion: { get: EP.FILE_FORMULATION, create: EP.FILE_FORMULATION_CREATE, respuestaKey: "formulacion_cargos" },
  apertura: { get: EP.FILE_OPENING_PROBATIONARY, create: EP.FILE_OPENING_PROBATIONARY_CREATE, respuestaKey: "apertura_etapa_probatoria" },
  cierre: { get: EP.FILE_CLOSING_PROBATIONARY, create: EP.FILE_CLOSING_PROBATIONARY_CREATE, respuestaKey: "cierre_etapa_probatoria" },
  decision: { get: EP.FILE_DECISION, create: EP.FILE_DECISION_CREATE, respuestaKey: "decision_fondo" },
  recurso: { get: EP.FILE_RESOURCE, create: EP.FILE_RESOURCE_CREATE, respuestaKey: "recurso" },
  ejecucion: { get: EP.FILE_EXECUTION, create: EP.FILE_EXECUTION_CREATE, respuestaKey: "ejecucion_sancion" },
} satisfies Record<
  string,
  { get: (id: number) => string; create: (id: number) => string; respuestaKey: string }
>;

export type EtapaClave = keyof typeof ETAPAS_API;

/**
 * Datos de una etapa (`datos`, o `null` si aún no existe) y su condición de
 * creación (`creable`, en la raíz de la respuesta).
 *
 * `gcTime: 0` + `staleTime: 0`: cada vez que se monta la pestaña de la etapa se
 * vuelve a pedir (como antes con useEffect). El acto administrativo y los
 * documentos se mutan desde componentes que no conocen esta clave, así que una
 * caché viva mostraría datos viejos al volver a la pestaña.
 */
export function useEtapaQuery<T>(etapa: EtapaClave, expedienteId: number) {
  const cfg = ETAPAS_API[etapa];
  return useQuery({
    queryKey: sancionatorioKeys.etapa(expedienteId, etapa),
    queryFn: async () => {
      const res = await apiRequest<Record<string, unknown>>(cfg.get(expedienteId));
      return {
        datos: (res[cfg.respuestaKey] ?? null) as T | null,
        creable: (res.creable ?? null) as Creable | null,
      } satisfies EtapaRespuesta<T>;
    },
    enabled: !!expedienteId,
    staleTime: 0,
    gcTime: 0,
    retry: false,
  });
}

/** Crea la etapa (POST). Devuelve el `etapa_id` nuevo. */
export function useCrearEtapaMutation(etapa: EtapaClave, expedienteId: number) {
  const cfg = ETAPAS_API[etapa];
  return useMutation({
    mutationFn: async () => {
      const res = await apiRequest<{ etapa_id?: number }>(cfg.create(expedienteId), {
        method: "POST",
      });
      if (!res.etapa_id) throw new ApiError(500, "Error al crear la etapa.");
      return res.etapa_id;
    },
  });
}

async function getCatalogo(endpoint: string): Promise<TipoCatalogo[]> {
  const res = await apiRequest<{ data?: TipoCatalogo[] }>(endpoint);
  return res.data ?? [];
}

/** Tipos de medida preventiva (catálogo). */
export function useTiposMedidaQuery() {
  return useQuery({
    queryKey: sancionatorioKeys.tiposMedida(),
    queryFn: () => getCatalogo(EP.FILE_TIPO_MEDIDA),
  });
}

/** Tipos de sanción de la decisión de fondo (catálogo). */
export function useTiposSancionQuery() {
  return useQuery({
    queryKey: sancionatorioKeys.tiposSancion(),
    queryFn: () => getCatalogo(EP.FILE_TIPO_SANCION),
  });
}

/** Tipos de cesación (catálogo). */
export function useTiposCesacionQuery() {
  return useQuery({
    queryKey: sancionatorioKeys.tiposCesacion(),
    queryFn: () => getCatalogo(EP.FILE_TIPO_CESACION),
  });
}

/**
 * Medida preventiva migrable desde infracciones (mismo radicado). Opcional:
 * los errores se ignoran (la consulta queda en `null`).
 */
export function useMigracionMedidaQuery(radicado: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: sancionatorioKeys.migracionMedida(radicado ?? ""),
    queryFn: async () => {
      try {
        return await apiRequest<MigracionMedida>(
          INFRACTION_ENDPOINTS.INFRACTION_MIGRATION_MEDIDA(radicado ?? ""),
        );
      } catch {
        return null;
      }
    },
    enabled: enabled && !!radicado,
    staleTime: 0,
    gcTime: 0,
    retry: false,
  });
}

/**
 * Importa la medida preventiva desde infracciones: crea la etapa, su acto (+
 * comunicación) y adjunta el informe técnico. Lanza `ApiError` con el mensaje
 * del paso que falló.
 */
export function useImportarMedidaMutation(expedienteId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (migracion: MigracionMedida) => {
      const fallo = (e: unknown, msg: string) =>
        e instanceof ApiError && e.data?.detail ? e : new ApiError(0, msg);

      let etapaId: number | undefined;
      try {
        const res = await apiRequest<{ etapa_id?: number }>(EP.FILE_MEASURE_CREATE(expedienteId), {
          method: "POST",
          body: JSON.stringify({
            tipo_medida_id: migracion.medida.tipo_medida_id,
            cantidad: migracion.medida.cantidad,
            especie: migracion.medida.especie,
            estado_medida: migracion.medida.estado_medida,
          }),
        });
        etapaId = res.etapa_id;
      } catch (e) {
        throw fallo(e, "Error al importar datos");
      }

      if (migracion.acto && etapaId) {
        const acto = migracion.acto;
        const fd = new FormData();
        fd.append("expediente_id", String(expedienteId));
        fd.append("tipo_acto", acto.tipo_acto);
        fd.append("numerado", String(acto.numerado));
        fd.append("fecha_numerado", acto.fecha_numerado ?? "");
        fd.append("documento_acto_administrativo_id", String(acto.documento_acto_administrativo_id));
        fd.append("etapa_tipo", "etapa_medida_preventiva");
        fd.append("etapa_ref_id", String(etapaId));
        let actoId: number | undefined;
        try {
          const res = await apiRequest<{ data?: { id?: number } }>(EP.FILE_ACTO_ADMIN, {
            method: "POST",
            body: fd,
          });
          actoId = res.data?.id;
        } catch (e) {
          throw fallo(e, "Error al importar el acto administrativo");
        }

        const com = acto.comunicacion;
        if (com && com.documento_comunicacion_id && actoId) {
          const cfd = new FormData();
          cfd.append("expediente_id", String(expedienteId));
          cfd.append("acto_admin_id", String(actoId));
          cfd.append("numerado", String(com.numerado).padStart(4, "0"));
          cfd.append("fecha_numerado", com.fecha_numerado ?? "");
          cfd.append("fecha_envio", com.fecha_envio ?? "");
          cfd.append("documento_comunicacion_id", String(com.documento_comunicacion_id));
          try {
            await apiRequest(EP.FILE_COMUNICACION, { method: "POST", body: cfd });
          } catch (e) {
            throw fallo(e, "Error al importar la comunicación del acto");
          }
        }
      }

      // El informe técnico es opcional: un fallo aquí no aborta la importación.
      if (migracion.informe_tecnico_documento_id && etapaId) {
        await apiRequest(EP.FILE_POST_DOC_ATTACHED(etapaId), {
          method: "POST",
          body: JSON.stringify({
            nombre: "Informe Tecnico",
            documento_anexo_id: migracion.informe_tecnico_documento_id,
            etapa_tipo: "etapa_medida_preventiva",
          }),
        }).catch(() => undefined);
      }
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: sancionatorioKeys.etapa(expedienteId, "medida") }),
  });
}

/** Archiva el expediente (PATCH). */
export function useArchivarExpedienteMutation(expedienteId: number) {
  return useMutation({
    mutationFn: () => apiRequest(EP.FILE_ARCHIVE(expedienteId), { method: "PATCH" }),
  });
}
