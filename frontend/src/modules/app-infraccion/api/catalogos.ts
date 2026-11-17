import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest, INFRACTION_ENDPOINTS } from "@shared/lib/api";
import { useErrorToast } from "@shared/hooks/useErrorToast";
import type { Toast } from "@shared/lib/toastService";
import type { ModeloGenerico, Municipio } from "@shared/types/common";
import type { Quejoso, TipoAfectacion } from "../types";
import { infraccionKeys } from "./queryKeys";

/** Catálogos casi fijos: se reutilizan 5 min entre pantallas. */
const STALE_CATALOGO = 5 * 60_000;

async function listar<T>(endpoint: string): Promise<T[]> {
  return (await apiRequest<{ data?: T[] | null }>(endpoint)).data ?? [];
}

/** Municipios con sus veredas. */
export function useMunicipiosQuery() {
  return useQuery({
    queryKey: infraccionKeys.municipios(),
    queryFn: () => listar<Municipio>(INFRACTION_ENDPOINTS.INFRACTION_TOWNS_RURAL_DISTRICT),
    staleTime: STALE_CATALOGO,
  });
}

/** Recursos naturales afectados (agua, suelo...). */
export function useRecursosAfectadosQuery() {
  return useQuery({
    queryKey: infraccionKeys.recursosAfectados(),
    queryFn: () => listar<ModeloGenerico>(INFRACTION_ENDPOINTS.INFRACTION_AFFECTED_RESOURCE),
    staleTime: STALE_CATALOGO,
  });
}

/** Tipos de afectación (cada uno ligado a un recurso). */
export function useTiposAfectacionQuery() {
  return useQuery({
    queryKey: infraccionKeys.tiposAfectacion(),
    queryFn: () => listar<TipoAfectacion>(INFRACTION_ENDPOINTS.INFRACTION_TIPOS_AFECTACION),
    staleTime: STALE_CATALOGO,
  });
}

/** Quejosos / denunciantes registrados. Crece desde los formularios. */
export function useQuejososQuery() {
  return useQuery({
    queryKey: infraccionKeys.quejosos(),
    queryFn: () => listar<Quejoso>(INFRACTION_ENDPOINTS.INFRACTION_COMPLAINER),
  });
}

/**
 * Reemplaza la lista de quejosos en caché. Los formularios (nuevo expediente,
 * información) crean el quejoso y entregan la lista ya ampliada para poder
 * seleccionarlo al instante, sin esperar un refetch.
 */
export function useSetQuejosos() {
  const queryClient = useQueryClient();
  return useCallback(
    (quejosos: Quejoso[]) => queryClient.setQueryData(infraccionKeys.quejosos(), quejosos),
    [queryClient],
  );
}

const SIN_MUNICIPIOS: Municipio[] = [];
const SIN_RECURSOS: ModeloGenerico[] = [];
const SIN_TIPOS: TipoAfectacion[] = [];
const SIN_QUEJOSOS: Quejoso[] = [];

/**
 * Los cuatro catálogos que necesitan las pantallas de gestión y consulta
 * (lista lateral + detalle), con un toast por cada carga fallida.
 */
export function useCatalogosInfraccion(setToast: (toast: Toast) => void) {
  const municipios = useMunicipiosQuery();
  const recursos = useRecursosAfectadosQuery();
  const tipos = useTiposAfectacionQuery();
  const quejosos = useQuejososQuery();
  const setQuejosos = useSetQuejosos();

  useErrorToast(municipios.error, setToast, "Error al cargar los municipios");
  useErrorToast(recursos.error, setToast, "Error al cargar los recursos afectados");
  useErrorToast(tipos.error, setToast, "Error al cargar los tipos de afectación");
  useErrorToast(quejosos.error, setToast, "Error al cargar los quejosos");

  return {
    municipios: municipios.data ?? SIN_MUNICIPIOS,
    recursos: recursos.data ?? SIN_RECURSOS,
    tiposAfectacion: tipos.data ?? SIN_TIPOS,
    quejosos: quejosos.data ?? SIN_QUEJOSOS,
    setQuejosos,
    cargando: municipios.isPending || recursos.isPending || tipos.isPending || quejosos.isPending,
  };
}
