import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { useInformesQuery, type FiltrosInformes } from "../../api/informes";

export const TIPO_INFORME_OPTIONS = ["VISITA", "SEGUIMIENTO"];

export const FILTROS_INFORMES_VACIOS: FiltrosInformes = {
  fechaDesde: "",
  fechaHasta: "",
  aceptado: "",
  profesionalId: "",
  radicado: "",
  tipo: "",
};

/**
 * Filtros + paginación del listado de informes técnicos (/informes). Los datos
 * vienen de react-query: cambiar un filtro vuelve a la página 1.
 */
export function useInformesTecnicos() {
  const location = useLocation();
  const [filtros, setFiltrosState] = useState<FiltrosInformes>(FILTROS_INFORMES_VACIOS);
  const [page, setPage] = useState(1);
  const query = useInformesQuery(filtros, page);

  // Filtro por expediente desde navegación (ej: desde GestionInfraccionLayout).
  useEffect(() => {
    const state = location.state as { expedienteRadicadoToFilter?: string } | null;
    if (state?.expedienteRadicadoToFilter) {
      setFiltrosState({ ...FILTROS_INFORMES_VACIOS, radicado: state.expedienteRadicadoToFilter });
      setPage(1);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  const setFiltros = (parcial: Partial<FiltrosInformes>) => {
    setFiltrosState((prev) => ({ ...prev, ...parcial }));
    setPage(1);
  };

  const hasActiveFilters = Object.entries(filtros).some(
    ([clave, valor]) => valor !== FILTROS_INFORMES_VACIOS[clave as keyof FiltrosInformes],
  );

  return {
    informes: query.data?.data ?? [],
    profesionales: query.data?.profesionales_disponibles ?? [],
    revisores: query.data?.revisores_disponibles ?? [],
    totalCount: query.data?.total ?? 0,
    totalPages: query.data?.total_pages ?? 1,
    loading: query.isPending,
    fetching: query.isFetching,
    isError: query.isError,
    refetch: query.refetch,
    page,
    setPage,
    filtros,
    setFiltros,
    clearFilters: () => {
      setFiltrosState(FILTROS_INFORMES_VACIOS);
      setPage(1);
    },
    hasActiveFilters,
  };
}

export type InformesTecnicosState = ReturnType<typeof useInformesTecnicos>;
