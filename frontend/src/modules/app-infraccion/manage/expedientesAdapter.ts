import { apiRequest, INFRACTION_ENDPOINTS, jsonBody } from "@shared/lib/api";
import type { ModeloGenerico } from "@shared/types/common";
import {
  filtroArchivado,
  filtroMunicipio,
  filtroPorCampo,
  type ExpedientesAdapter,
  type ExpedientesConfig,
  type FiltroAvanzadoBase,
  type FiltroRapido,
} from "@features/expedientes";
import type { Expediente } from "../types";
import { ETAPAS_PROCESO } from "./etapasProceso";

const SIN_ETAPA = "sin-etapa";

/**
 * Filtro rápido por etapa actual: opciones fijas en el orden del proceso
 * (código del backend -> etiqueta) más "Sin etapa".
 */
const filtroEtapa: FiltroRapido<Expediente> = {
  id: "etapa",
  tipo: "fijo",
  etiquetaTodos: "Todas las etapas",
  opciones: [
    ...ETAPAS_PROCESO.map((e) => ({ value: e.codigo, label: e.etiqueta })),
    { value: SIN_ETAPA, label: "Sin etapa" },
  ],
  coincide: (e, v) => (v === SIN_ETAPA ? !e.etapa_actual : e.etapa_actual === v),
};

/** Filtros avanzados de infracción: los comunes + tipos de afectación. */
export type FiltroAvanzadoInfraccion = FiltroAvanzadoBase & {
  tipo_afectacion_ids?: number[];
};

/**
 * Alcance de la búsqueda avanzada: `propios` (vista de gestión, solo los del
 * abogado responsable) o `todos` (vista de consulta; el backend lo exige con
 * `infraccion_consultar` y, sin él, vuelve a `propios`).
 */
export type AlcanceExpedientes = "propios" | "todos";

export function crearExpedientesInfraccionAdapter(
  alcance: AlcanceExpedientes,
): ExpedientesAdapter<Expediente, FiltroAvanzadoInfraccion> {
  return {
    queryKey: ["app-infraccion", "expedientes", alcance],
    filtrarAvanzado: async (filtros) =>
      (
        await apiRequest<{ data?: Expediente[] }>(INFRACTION_ENDPOINTS.INFRACTION_FILTER, {
          method: "POST",
          ...jsonBody({ ...filtros, alcance }),
        })
      ).data ?? [],
    obtenerVeredas: async (municipioId) =>
      (
        await apiRequest<{ veredas?: ModeloGenerico[] }>(
          INFRACTION_ENDPOINTS.INFRACTION_RURAL_DISTRICT_BY_TOWN(municipioId),
        )
      ).veredas ?? [],
  };
}

const adapters: Record<AlcanceExpedientes, ExpedientesAdapter<Expediente, FiltroAvanzadoInfraccion>> = {
  propios: crearExpedientesInfraccionAdapter("propios"),
  todos: crearExpedientesInfraccionAdapter("todos"),
};

/** Adapter estable por alcance (misma referencia entre renders). */
export const expedientesInfraccionAdapter = (alcance: AlcanceExpedientes) => adapters[alcance];

export const expedientesInfraccionConfig: ExpedientesConfig<Expediente, FiltroAvanzadoInfraccion> = {
  campoDestacado: { etiqueta: "Fecha Radicado", valor: (e) => e.fecha_radicado },
  filtrosRapidos: [
    filtroMunicipio<Expediente>(),
    filtroEtapa,
    filtroArchivado<Expediente>("Todos"),
    filtroPorCampo<Expediente>("estado", "Todos los estados", (e) => e.estado),
  ],
  camposTextoAvanzado: [
    { clave: "direccion", etiqueta: "Dirección", placeholder: "Buscar por dirección..." },
  ],
};
