import { apiRequest, jsonBody, SANCTIONING_ENDPOINTS } from "@shared/lib/api";
import type { ModeloGenerico } from "@shared/types/common";
import type { Expediente } from "@shared/types/sancionatorio";
import {
  filtroArchivado,
  filtroMunicipio,
  filtroPorCampo,
  type ExpedientesAdapter,
  type ExpedientesConfig,
  type FiltroAvanzadoBase,
} from "@features/expedientes";

/** Filtros avanzados de sancionatorio: los comunes + motivo de afectación. */
export type FiltroAvanzadoSancionatorio = FiltroAvanzadoBase & {
  motivo_afectacion?: string;
};

export const expedientesSancionatorioAdapter: ExpedientesAdapter<
  Expediente,
  FiltroAvanzadoSancionatorio
> = {
  queryKey: ["app-sancionatorio", "expedientes"],
  filtrarAvanzado: async (filtros) =>
    (
      await apiRequest<{ data?: Expediente[] }>(SANCTIONING_ENDPOINTS.FILE_FILTER, {
        method: "POST",
        ...jsonBody(filtros),
      })
    ).data ?? [],
  obtenerVeredas: async (municipioId) =>
    (
      await apiRequest<{ veredas?: ModeloGenerico[] }>(
        SANCTIONING_ENDPOINTS.TOWNS_SIDEWALK_BY_TOWN(municipioId),
      )
    ).veredas ?? [],
};

export const expedientesSancionatorioConfig: ExpedientesConfig<
  Expediente,
  FiltroAvanzadoSancionatorio
> = {
  campoDestacado: { etiqueta: "Expediente", valor: (e) => e.expediente },
  filtrosRapidos: [
    filtroMunicipio<Expediente>(),
    filtroPorCampo<Expediente>("etapa", "Todas las etapas", (e) => e.ultima_etapa),
    // La etiqueta "Todos los estados" es la que ya tenía este select en sancionatorio.
    filtroArchivado<Expediente>("Todos los estados"),
  ],
  camposTextoAvanzado: [
    { clave: "motivo_afectacion", etiqueta: "Motivo de afectación", placeholder: "Buscar por motivo..." },
    { clave: "direccion", etiqueta: "Dirección", placeholder: "Buscar por dirección..." },
  ],
};
