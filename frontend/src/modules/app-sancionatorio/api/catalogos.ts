import { useQuery } from "@tanstack/react-query";
import { apiRequest, SANCTIONING_ENDPOINTS as EP } from "@shared/lib/api";
import { useErrorToast } from "@shared/hooks/useErrorToast";
import type { Toast } from "@shared/lib/toastService";
import type { ModeloGenerico, Municipio } from "@shared/types/common";
import { sancionatorioKeys } from "./queryKeys";

/** Catálogos casi fijos: se reutilizan 5 min entre pantallas. */
const STALE_CATALOGO = 5 * 60_000;

async function listar<T>(endpoint: string): Promise<T[]> {
  return (await apiRequest<{ data?: T[] | null }>(endpoint)).data ?? [];
}

/** Municipios con sus veredas. */
export function useMunicipiosQuery() {
  return useQuery({
    queryKey: sancionatorioKeys.municipios(),
    queryFn: () => listar<Municipio>(EP.TOWNS_SIDEWALK),
    staleTime: STALE_CATALOGO,
  });
}

/** Recursos naturales afectados. */
export function useRecursosAfectadosQuery() {
  return useQuery({
    queryKey: sancionatorioKeys.recursosAfectados(),
    queryFn: () => listar<ModeloGenerico>(EP.FILE_AFFECTED_RESOURCE),
    staleTime: STALE_CATALOGO,
  });
}

const SIN_MUNICIPIOS: Municipio[] = [];
const SIN_RECURSOS: ModeloGenerico[] = [];

/**
 * Catálogos de las pantallas de gestión y consulta (lista lateral + detalle),
 * con un toast por cada carga fallida.
 */
export function useCatalogosSancionatorio(setToast: (toast: Toast) => void) {
  const municipios = useMunicipiosQuery();
  const recursos = useRecursosAfectadosQuery();

  useErrorToast(municipios.error, setToast, "Error al cargar los municipios");
  useErrorToast(recursos.error, setToast, "Error al cargar los recursos afectados");

  return {
    municipios: municipios.data ?? SIN_MUNICIPIOS,
    recursos: recursos.data ?? SIN_RECURSOS,
    cargando: municipios.isPending || recursos.isPending,
  };
}
