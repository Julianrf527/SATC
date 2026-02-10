import { useEffect, useMemo, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import { useNavigate } from "react-router-dom";
import TitleForm from "../../Label/TitleForm";

// Tipos para la nueva estructura de alertas
type EstadoSemaforo = "verde" | "amarillo" | "rojo" | "vencido";

type Semaforo = {
  estado: EstadoSemaforo;
  color_hex: string;
  porcentaje_avance: number;
  urgencia: "baja" | "media" | "alta" | "critico";
  dias_transcurridos: number;
  dias_restantes: number;
  dias_totales: number;
  esta_vencido: boolean;
};

type Alerta = {
  tipo: string;
  etapa: string;
  accion_requerida: string;
  plazo_legal: string;
  msg: string;
  fecha_inicio?: string;
  fecha_notificacion?: string;
  fecha_presentacion?: string;
  fecha_limite: string;
  semaforo: Semaforo;
};

type AlertasExpediente = {
  [alertaKey: string]: Alerta;
};

type EstadisticasSemaforo = {
  verde: number;
  amarillo: number;
  rojo: number;
  vencido: number;
};

type ResponseAlertas = {
  ok: boolean;
  alertas: {
    [radicado: string]: AlertasExpediente;
  };
  total_expedientes: number;
  expedientes_con_alertas: number;
  estadisticas_semaforo: EstadisticasSemaforo;
};

type AlertaFlat = {
  radicado: string;
  alertaKey: string;
  tipo: string;
  etapa: string;
  accion_requerida: string;
  plazo_legal: string;
  msg: string;
  fecha_limite: string;
  semaforo: Semaforo;
};

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function AlertsLayout({ setToast }: Props) {
  const navigate = useNavigate();
  const [alertasData, setAlertasData] = useState<ResponseAlertas | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Filtros
  const [radicadoFilter, setRadicadoFilter] = useState("");
  const [estadoFilter, setEstadoFilter] = useState<string>("all");
  const [tipoFilter, setTipoFilter] = useState<string>("all");

  // Paginación
  const [page, setPage] = useState(1);
  const rowsPerPage = 10;

  useEffect(() => {
    loadAlertas();
  }, []);

  const loadAlertas = async () => {
    try {
      setIsLoading(true);
      const res = await apiCall(API_CONFIG.ENDPOINTS.FILE_ALERTS_ALL, {
        method: "GET",
      });

      if (res.ok) {
        setAlertasData(res);
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al cargar las alertas",
          type: "error",
        });
      }
    } catch (error) {
      console.error("Error cargando alertas:", error);
      setToast({
        id: Date.now(),
        message: "Error al cargar las alertas",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Convertir estructura anidada a flat
  const alertasFlat = useMemo(() => {
    if (!alertasData) return [];

    const flat: AlertaFlat[] = [];

    Object.entries(alertasData.alertas).forEach(
      ([radicado, alertasExpediente]) => {
        Object.entries(alertasExpediente).forEach(([alertaKey, alerta]) => {
          flat.push({
            radicado,
            alertaKey,
            ...alerta,
          });
        });
      }
    );

    return flat;
  }, [alertasData]);

  // Obtener tipos únicos para el filtro
  const tiposUnicos = useMemo(() => {
    const tipos = new Set(alertasFlat.map((a) => a.tipo));
    return Array.from(tipos).sort();
  }, [alertasFlat]);

  // Filtrado y ordenamiento
  const alertasFiltradas = useMemo(() => {
    const radicado = radicadoFilter.trim().toLowerCase();

    let filtered = alertasFlat.filter((a) => {
      const matchesRadicado = radicado
        ? a.radicado.toLowerCase().includes(radicado)
        : true;
      const matchesEstado =
        estadoFilter === "all" ? true : a.semaforo.estado === estadoFilter;
      const matchesTipo = tipoFilter === "all" ? true : a.tipo === tipoFilter;

      return matchesRadicado && matchesEstado && matchesTipo;
    });

    // Ordenar por urgencia y porcentaje de avance
    filtered.sort((a, b) => {
      const urgenciaOrder = { critico: 0, alta: 1, media: 2, baja: 3 };
      const urgA = urgenciaOrder[a.semaforo.urgencia];
      const urgB = urgenciaOrder[b.semaforo.urgencia];

      if (urgA !== urgB) return urgA - urgB;
      return b.semaforo.porcentaje_avance - a.semaforo.porcentaje_avance;
    });

    return filtered;
  }, [alertasFlat, radicadoFilter, estadoFilter, tipoFilter]);

  // Paginación
  const startIndex = (page - 1) * rowsPerPage;
  const endIndex = startIndex + rowsPerPage;
  const paginatedData = alertasFiltradas.slice(startIndex, endIndex);
  const totalPages = Math.max(
    1,
    Math.ceil(alertasFiltradas.length / rowsPerPage)
  );

  // Resetear página cuando cambian los filtros
  useEffect(() => {
    setPage(1);
  }, [radicadoFilter, estadoFilter, tipoFilter]);

  const handleGoToExpediente = (radicado: string) => {
    navigate("/file/manage", {
      state: {
        radicadoToSelect: radicado,
        timestamp: Date.now(),
      },
    });
  };

  const getSemaforoBadge = (semaforo: Semaforo) => {
    const configs = {
      verde: {
        class: "badge-success",
        icon: (
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
              clipRule="evenodd"
            />
          </svg>
        ),
        label: "Verde",
      },
      amarillo: {
        class: "badge-warning",
        icon: (
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        ),
        label: "Amarillo",
      },
      rojo: {
        class: "badge-error",
        icon: (
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
              clipRule="evenodd"
            />
          </svg>
        ),
        label: "Rojo",
      },
      vencido: {
        class: "badge-error opacity-80",
        icon: (
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M13.477 14.89A6 6 0 015.11 6.524l8.367 8.368zm1.414-1.414L6.524 5.11a6 6 0 018.367 8.367zM18 10a8 8 0 11-16 0 8 8 0 0116 0z"
              clipRule="evenodd"
            />
          </svg>
        ),
        label: "Vencido",
      },
    };

    const config = configs[semaforo.estado];

    return (
      <div className="flex flex-col items-center gap-1">
        <span className={`badge ${config.class} gap-1 text-white`}>
          {config.icon}
          {config.label}
        </span>
        <span className="text-xs text-base-content/60 font-mono">
          {semaforo.porcentaje_avance.toFixed(0)}%
        </span>
      </div>
    );
  };

  const getProgressBar = (semaforo: Semaforo) => {
    return (
      <div className="flex flex-col gap-1 w-full">
        <div className="w-full bg-base-300 rounded-full h-2 overflow-hidden">
          <div
            className="h-2 rounded-full transition-all duration-300"
            style={{
              width: `${Math.min(semaforo.porcentaje_avance, 100)}%`,
              backgroundColor: semaforo.color_hex,
            }}
          />
        </div>
        <div className="flex justify-between text-xs text-base-content/60">
          <span>{semaforo.dias_transcurridos} días</span>
          <span>
            {semaforo.esta_vencido ? (
              <span className="text-error font-semibold">Vencido</span>
            ) : (
              `${semaforo.dias_restantes} días restantes`
            )}
          </span>
        </div>
      </div>
    );
  };

  const formatFecha = (fecha: string) => {
    try {
      const date = new Date(fecha);
      return date.toLocaleDateString("es-CO", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return fecha;
    }
  };

  const getTipoLabel = (tipo: string) => {
    const labels: Record<string, string> = {
      inicio_sancionatorio: "Inicio Sancionatorio",
      decision_fondo: "Decisión de Fondo",
      presentacion_descargos: "Descargos",
      informe_tecnico: "Informe Técnico",
      alegato_conclusion: "Alegato de Conclusión",
      presentacion_recurso: "Presentar Recurso",
      resolucion_recurso: "Resolución Recurso",
      notificacion_recurso: "Notificación Recurso",
    };
    return labels[tipo] || tipo;
  };

  if (isLoading) {
    return (
      <div className="bg-base-200 min-h-screen">
        <section className="w-full h-full flex justify-center items-start min-h-[calc(100vh-4rem)] overflow-hidden p-4">
          <div className="w-full max-w-7xl h-full">
            <div className="card bg-base-100 shadow-xl border border-base-300 w-full h-full">
              <div className="card-body flex items-center justify-center">
                <div className="loading loading-spinner loading-lg"></div>
                <p className="ml-4 text-gray-600">Cargando alertas...</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="bg-base-200 min-h-screen">
      <section className="w-full h-full flex justify-center items-start min-h-[calc(100vh-4rem)] overflow-hidden p-4">
        <div className="w-full max-w-7xl h-full">
          <div className="card bg-base-100 shadow-xl border border-base-300 w-full h-full">
            <div className="card-body px-6 py-6 flex flex-col h-full overflow-hidden">
              <TitleForm
                title="Sistema de Alertas de Expedientes"
                body="Monitorea los plazos legales y urgencias de tus expedientes con semaforización en tiempo real"
              />

              {/* Estadísticas con semáforo */}
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
                <div className="stats shadow border border-base-300">
                  <div className="stat">
                    <div className="stat-title text-xs">Total Alertas</div>
                    <div className="stat-value text-2xl">
                      {alertasFlat.length}
                    </div>
                    <div className="stat-desc">
                      {alertasData?.expedientes_con_alertas || 0} expedientes
                    </div>
                  </div>
                </div>

                <div className="stats shadow border-2 border-success bg-success/5">
                  <div className="stat">
                    <div className="stat-title text-xs">🟢 Verde</div>
                    <div className="stat-value text-2xl text-success">
                      {alertasData?.estadisticas_semaforo?.verde || 0}
                    </div>
                    <div className="stat-desc">Tiempo suficiente</div>
                  </div>
                </div>

                <div className="stats shadow border-2 border-warning bg-warning/5">
                  <div className="stat">
                    <div className="stat-title text-xs">🟡 Amarillo</div>
                    <div className="stat-value text-2xl text-warning">
                      {alertasData?.estadisticas_semaforo?.amarillo || 0}
                    </div>
                    <div className="stat-desc">Atención requerida</div>
                  </div>
                </div>

                <div className="stats shadow border-2 border-error bg-error/5">
                  <div className="stat">
                    <div className="stat-title text-xs">🔴 Rojo</div>
                    <div className="stat-value text-2xl text-error">
                      {alertasData?.estadisticas_semaforo?.rojo || 0}
                    </div>
                    <div className="stat-desc">Urgente</div>
                  </div>
                </div>

                <div className="stats shadow border-2 border-error bg-error/10">
                  <div className="stat">
                    <div className="stat-title text-xs">⚫ Vencido</div>
                    <div className="stat-value text-2xl text-error">
                      {alertasData?.estadisticas_semaforo?.vencido || 0}
                    </div>
                    <div className="stat-desc">Crítico</div>
                  </div>
                </div>
              </div>

              {/* Filtros uniformes y alineados */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div className="form-control">
                  <label className="label py-0 pb-2">
                    <span className="label-text font-semibold">Radicado</span>
                  </label>
                  <input
                    className="input input-bordered w-full"
                    placeholder="Buscar por radicado..."
                    value={radicadoFilter}
                    onChange={(e) => setRadicadoFilter(e.target.value)}
                  />
                </div>

                <div className="form-control">
                  <label className="label py-0 pb-2">
                    <span className="label-text font-semibold">Estado</span>
                  </label>
                  <select
                    className="select select-bordered w-full"
                    value={estadoFilter}
                    onChange={(e) => setEstadoFilter(e.target.value)}
                  >
                    <option value="all">Todos los estados</option>
                    <option value="verde">🟢 Verde</option>
                    <option value="amarillo">🟡 Amarillo</option>
                    <option value="rojo">🔴 Rojo</option>
                    <option value="vencido">⚫ Vencido</option>
                  </select>
                </div>

                <div className="form-control">
                  <label className="label py-0 pb-2">
                    <span className="label-text font-semibold">
                      Tipo de Alerta
                    </span>
                  </label>
                  <select
                    className="select select-bordered w-full"
                    value={tipoFilter}
                    onChange={(e) => setTipoFilter(e.target.value)}
                  >
                    <option value="all">Todos los tipos</option>
                    {tiposUnicos.map((tipo) => (
                      <option key={tipo} value={tipo}>
                        {getTipoLabel(tipo)}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Tabla */}
              <div className="flex flex-col flex-1 overflow-hidden">
                <div className="flex flex-col flex-1 overflow-hidden border border-base-300 rounded-lg">
                  <div className="overflow-auto">
                    <table className="table table-zebra w-full">
                      <thead className="sticky top-0 bg-base-200 z-10">
                        <tr>
                          <th className="font-semibold">Semáforo</th>
                          <th className="font-semibold">Radicado</th>
                          <th className="font-semibold">Etapa</th>
                          <th className="font-semibold">Tipo</th>
                          <th className="font-semibold">Acción Requerida</th>
                          <th className="font-semibold w-64">Progreso</th>
                          <th className="font-semibold">Plazo Legal</th>
                          <th className="font-semibold">Fecha Límite</th>
                          <th className="font-semibold">Acciones</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedData.length === 0 ? (
                          <tr>
                            <td colSpan={9} className="text-center py-12">
                              <div className="flex flex-col items-center gap-2">
                                <svg
                                  className="w-12 h-12 text-base-content/30"
                                  fill="none"
                                  stroke="currentColor"
                                  viewBox="0 0 24 24"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                                  />
                                </svg>
                                <span className="text-base-content/60 font-medium">
                                  No hay alertas
                                </span>
                                <span className="text-base-content/40 text-sm">
                                  {radicadoFilter ||
                                  estadoFilter !== "all" ||
                                  tipoFilter !== "all"
                                    ? "Intenta ajustar los filtros"
                                    : "¡Todo está al día!"}
                                </span>
                              </div>
                            </td>
                          </tr>
                        ) : (
                          paginatedData.map((alerta, index) => (
                            <tr
                              key={`${alerta.radicado}-${alerta.alertaKey}-${index}`}
                              className="hover"
                            >
                              <td>{getSemaforoBadge(alerta.semaforo)}</td>
                              <td className="font-mono text-sm font-semibold">
                                {alerta.radicado}
                              </td>
                              <td className="text-sm">
                                <div className="badge badge-ghost badge-sm">
                                  {alerta.etapa}
                                </div>
                              </td>
                              <td className="text-sm">
                                <div className="badge badge-outline badge-sm">
                                  {getTipoLabel(alerta.tipo)}
                                </div>
                              </td>
                              <td className="text-sm max-w-xs">
                                <div
                                  className="tooltip tooltip-right"
                                  data-tip={alerta.msg}
                                >
                                  <p className="truncate">
                                    {alerta.accion_requerida}
                                  </p>
                                </div>
                              </td>
                              <td className="w-64">
                                {getProgressBar(alerta.semaforo)}
                              </td>
                              <td className="text-sm">
                                <span className="badge badge-info badge-sm text-white">
                                  {alerta.plazo_legal}
                                </span>
                              </td>
                              <td className="text-sm">
                                <div className="flex flex-col">
                                  <span className="font-semibold">
                                    {formatFecha(alerta.fecha_limite)}
                                  </span>
                                  {alerta.semaforo.esta_vencido && (
                                    <span className="text-error text-xs font-semibold">
                                      ¡Vencido!
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td>
                                <button
                                  className="btn btn-primary btn-sm text-white gap-1"
                                  onClick={() =>
                                    handleGoToExpediente(alerta.radicado)
                                  }
                                  title="Ver expediente"
                                >
                                  <svg
                                    className="w-4 h-4"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                                    />
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth={2}
                                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                                    />
                                  </svg>
                                  Gestionar
                                </button>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Paginación */}
                <div className="flex justify-between items-center pt-4 border-t border-base-300 mt-4">
                  <div className="text-sm text-base-content/60">
                    Mostrando {paginatedData.length} de{" "}
                    {alertasFiltradas.length} alerta
                    {alertasFiltradas.length !== 1 ? "s" : ""}
                  </div>
                  <div className="join">
                    <button
                      className="join-item btn btn-sm"
                      disabled={page === 1 || alertasFiltradas.length === 0}
                      onClick={() => setPage(page - 1)}
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M15 19l-7-7 7-7"
                        />
                      </svg>
                    </button>
                    <button className="join-item btn btn-sm no-animation">
                      Página {alertasFiltradas.length === 0 ? 0 : page} de{" "}
                      {totalPages}
                    </button>
                    <button
                      className="join-item btn btn-sm"
                      disabled={
                        page >= totalPages || alertasFiltradas.length === 0
                      }
                      onClick={() => setPage(page + 1)}
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 5l7 7-7 7"
                        />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
