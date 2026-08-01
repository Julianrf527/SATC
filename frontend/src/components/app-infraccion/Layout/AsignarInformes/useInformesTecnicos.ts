import { useEffect, useState, useCallback } from "react";
import { useLocation } from "react-router-dom";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import type {
  InformeTecnico,
  ProfesionalDisponible,
} from "../../../../types/infraccionApp";

export type ToastSetter = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;

export const TIPO_INFORME_OPTIONS = ["VISITA", "SEGUIMIENTO"];

/**
 * Estado de datos + filtros + paginación del listado de informes técnicos.
 */
export function useInformesTecnicos(setToast: ToastSetter) {
  const location = useLocation();

  // ── Datos ────────────────────────────────────────────────────────────────
  const [informes, setInformes] = useState<InformeTecnico[]>([]);
  const [profesionales, setProfesionales] = useState<ProfesionalDisponible[]>(
    [],
  );
  const [loading, setLoading] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const limit = 20;

  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [aceptado, setAceptado] = useState<"" | "true" | "false">("");
  const [profesionalFilter, setProfesionalFilter] = useState<number | "">("");
  const [expedienteRadicadoFilter, setExpedienteRadicadoFilter] = useState("");
  const [tipoInformeFilter, setTipoInformeFilter] = useState("");

  // Filtro por expediente desde navegación (ej: desde GestionInfraccionLayout)
  useEffect(() => {
    const state = location.state as { expedienteRadicadoToFilter?: string } | null;
    if (state?.expedienteRadicadoToFilter) {
      setExpedienteRadicadoFilter(state.expedienteRadicadoToFilter);
      window.history.replaceState({}, document.title);
    }
  }, [location]);

  // ── Carga de datos ────────────────────────────────────────────────────────
  const loadInformes = useCallback(
    async (currentPage = 1) => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.append("page", String(currentPage));
        params.append("limit", String(limit));
        if (fechaDesde) params.append("fecha_desde", fechaDesde);
        if (fechaHasta) params.append("fecha_hasta", fechaHasta);
        if (aceptado !== "") params.append("aceptado", aceptado);
        if (profesionalFilter !== "")
          params.append("profesional_id", String(profesionalFilter));
        if (expedienteRadicadoFilter.trim())
          params.append("expediente_radicado", expedienteRadicadoFilter.trim());
        if (tipoInformeFilter) params.append("tipo_informe", tipoInformeFilter);

        const res = await apiCall(
          `${API_CONFIG.ENDPOINTS.INFRACTION_REPORTS_LIST}?${params.toString()}`,
          { method: "GET" },
        );

        if (res.ok) {
          setInformes(res.data || []);
          setTotalCount(res.total ?? 0);
          setTotalPages(res.total_pages ?? 1);
          if (res.profesionales_disponibles) {
            setProfesionales(res.profesionales_disponibles);
          }
        } else {
          setToast({
            id: Date.now(),
            message: res.detail || "Error al cargar informes",
            type: "error",
          });
        }
      } catch {
        setToast({
          id: Date.now(),
          message: "Error de conexión",
          type: "error",
        });
      } finally {
        setLoading(false);
      }
    },
    [
      fechaDesde,
      fechaHasta,
      aceptado,
      profesionalFilter,
      expedienteRadicadoFilter,
      tipoInformeFilter,
    ],
  );

  useEffect(() => {
    setPage(1);
    loadInformes(1);
  }, [
    fechaDesde,
    fechaHasta,
    aceptado,
    profesionalFilter,
    expedienteRadicadoFilter,
    tipoInformeFilter,
  ]);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    loadInformes(newPage);
  };

  const clearFilters = () => {
    setFechaDesde("");
    setFechaHasta("");
    setAceptado("");
    setProfesionalFilter("");
    setExpedienteRadicadoFilter("");
    setTipoInformeFilter("");
    setPage(1);
  };

  const hasActiveFilters = !!(
    fechaDesde ||
    fechaHasta ||
    aceptado ||
    profesionalFilter ||
    expedienteRadicadoFilter ||
    tipoInformeFilter
  );

  return {
    informes,
    profesionales,
    loading,
    totalCount,
    totalPages,
    page,
    setPage,
    fechaDesde,
    setFechaDesde,
    fechaHasta,
    setFechaHasta,
    aceptado,
    setAceptado,
    profesionalFilter,
    setProfesionalFilter,
    expedienteRadicadoFilter,
    setExpedienteRadicadoFilter,
    tipoInformeFilter,
    setTipoInformeFilter,
    loadInformes,
    handlePageChange,
    clearFilters,
    hasActiveFilters,
  };
}

export type InformesTecnicosState = ReturnType<typeof useInformesTecnicos>;
