import { useEffect, useMemo, useState } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";

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

type ResponseAlertas = {
  ok: boolean;
  radicado: string;
  alertas: AlertasExpediente;
  total_alertas: number;
};

type AlertaFlat = {
  alertaKey: string;
  tipo: string;
  etapa: string;
  accion_requerida: string;
  plazo_legal: string;
  msg: string;
  fecha_limite: string;
  semaforo: Semaforo;
};

interface Props {
  expediente_id: number;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
}

export default function AlertasInfraccion({ expediente_id, setToast }: Props) {
  const [alertasData, setAlertasData] = useState<ResponseAlertas | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [estadoFilter, setEstadoFilter] = useState<string>("all");

  useEffect(() => {
    loadAlertas();
  }, [expediente_id]);

  const loadAlertas = async () => {
    try {
      setIsLoading(true);
      const res = await apiCall(API_CONFIG.ENDPOINTS.FILE_ALERTS(expediente_id), {
        method: "GET",
      });

      if (res.ok) {
        setAlertasData(res);
      } else {
        setToast?.({
          id: Date.now(),
          message: res.detail || "Error al cargar las alertas",
          type: "error",
        });
      }
    } catch (error) {
      /* console.error("Error cargando alertas:", error); */
      setToast?.({
        id: Date.now(),
        message: "Error al cargar las alertas",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Convertir estructura a flat
  const alertasFlat = useMemo(() => {
    if (!alertasData) return [];

    const flat: AlertaFlat[] = [];
    Object.entries(alertasData.alertas).forEach(([alertaKey, alerta]) => {
      flat.push({
        alertaKey,
        ...alerta,
      });
    });

    return flat;
  }, [alertasData]);

  // Calcular estadísticas
  const estadisticas = useMemo(() => {
    const stats = {
      verde: 0,
      amarillo: 0,
      rojo: 0,
      vencido: 0,
    };

    alertasFlat.forEach((a) => {
      stats[a.semaforo.estado]++;
    });

    return stats;
  }, [alertasFlat]);

  // Filtrado y ordenamiento
  const alertasFiltradas = useMemo(() => {
    let filtered = alertasFlat.filter((a) => {
      const matchesEstado =
        estadoFilter === "all" ? true : a.semaforo.estado === estadoFilter;
      return matchesEstado;
    });

    // Ordenar por urgencia y porcentaje
    filtered.sort((a, b) => {
      const urgenciaOrder = { critico: 0, alta: 1, media: 2, baja: 3 };
      const urgA = urgenciaOrder[a.semaforo.urgencia];
      const urgB = urgenciaOrder[b.semaforo.urgencia];

      if (urgA !== urgB) return urgA - urgB;
      return b.semaforo.porcentaje_avance - a.semaforo.porcentaje_avance;
    });

    return filtered;
  }, [alertasFlat, estadoFilter]);

  const getSemaforoIndicator = (semaforo: Semaforo) => {
    const configs = {
      verde: { emoji: "🟢", class: "text-success", label: "Verde" },
      amarillo: { emoji: "🟡", class: "text-warning", label: "Amarillo" },
      rojo: { emoji: "🔴", class: "text-error", label: "Rojo" },
      vencido: { emoji: "⚫", class: "text-error", label: "Vencido" },
    };

    const config = configs[semaforo.estado];

    return (
      <div className="flex items-center gap-2">
        <span className="text-lg">{config.emoji}</span>
        <div className="flex flex-col">
          <span className={`text-xs font-semibold ${config.class}`}>
            {config.label}
          </span>
          <span className="text-xs text-base-content/50 font-mono">
            {semaforo.porcentaje_avance.toFixed(0)}%
          </span>
        </div>
      </div>
    );
  };

  const getMiniProgressBar = (semaforo: Semaforo) => {
    return (
      <div className="flex items-center gap-2 w-full">
        <div className="flex-1 bg-base-300 rounded-full h-1.5 overflow-hidden">
          <div
            className="h-1.5 rounded-full transition-all"
            style={{
              width: `${Math.min(semaforo.porcentaje_avance, 100)}%`,
              backgroundColor: semaforo.color_hex,
            }}
          />
        </div>
        <span className="text-xs text-base-content/60 font-mono whitespace-nowrap">
          {semaforo.esta_vencido ? (
            <span className="text-error font-bold">¡Vencido!</span>
          ) : (
            `${semaforo.dias_restantes}d`
          )}
        </span>
      </div>
    );
  };

  const formatFecha = (fecha: string) => {
    try {
      const date = new Date(fecha);
      return date.toLocaleDateString("es-CO", {
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
      alegato_conclusion: "Alegato",
      presentacion_recurso: "Recurso",
      resolucion_recurso: "Resolución",
      notificacion_recurso: "Notificación",
    };
    return labels[tipo] || tipo;
  };

  if (isLoading) {
    return (
      <div className="card bg-base-100 shadow-sm border border-base-300">
        <div className="card-body p-4">
          <div className="flex items-center justify-center gap-3 py-6">
            <div className="loading loading-spinner loading-md"></div>
            <p className="text-sm text-base-content/60">Cargando alertas...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card bg-base-100 shadow-sm border border-base-300">
      <div className="card-body p-4">
        {/* Header compacto */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-warning/10 rounded-lg flex items-center justify-center">
              <svg
                className="w-4 h-4 text-warning"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-bold">Alertas de Plazos</h3>
              <p className="text-xs text-base-content/50">
                {alertasFlat.length}{" "}
                {alertasFlat.length === 1 ? "alerta" : "alertas"}
              </p>
            </div>
          </div>

          {/* Filtro compacto */}
          {alertasFlat.length > 0 && (
            <select
              className="select select-bordered select-xs w-32"
              value={estadoFilter}
              onChange={(e) => setEstadoFilter(e.target.value)}
            >
              <option value="all">Todos</option>
              <option value="verde">🟢 Verde</option>
              <option value="amarillo">🟡 Amarillo</option>
              <option value="rojo">🔴 Rojo</option>
              <option value="vencido">⚫ Vencido</option>
            </select>
          )}
        </div>

        {/* Estadísticas inline - solo si hay alertas */}
        {alertasFlat.length > 0 && (
          <div className="flex gap-2 mb-3">
            <div className="badge badge-success badge-sm gap-1">
              🟢 {estadisticas.verde}
            </div>
            <div className="badge badge-warning badge-sm gap-1">
              🟡 {estadisticas.amarillo}
            </div>
            <div className="badge badge-error badge-sm gap-1">
              🔴 {estadisticas.rojo}
            </div>
            {estadisticas.vencido > 0 && (
              <div className="badge badge-error badge-sm gap-1 opacity-80">
                ⚫ {estadisticas.vencido}
              </div>
            )}
          </div>
        )}

        {/* Lista de alertas o estado vacío */}
        {alertasFlat.length === 0 ? (
          <div className="bg-base-200 rounded-lg border border-base-300 p-6">
            <div className="text-center py-8">
              <div className="w-16 h-16 bg-base-300 rounded-full flex items-center justify-center mb-4 mx-auto">
                <svg
                  className="w-8 h-8 text-base-content/40"
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
              </div>
              <h3 className="text-base font-medium text-base-content/70 mb-1">
                Sin alertas pendientes
              </h3>
              <p className="text-sm text-base-content/60">
                No hay plazos legales próximos a vencer
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {alertasFiltradas.length === 0 ? (
              <div className="bg-base-200 rounded-lg border border-base-300 p-6">
                <div className="text-center py-6">
                  <div className="w-14 h-14 bg-base-300 rounded-full flex items-center justify-center mb-3 mx-auto">
                    <svg
                      className="w-7 h-7 text-base-content/40"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"
                      />
                    </svg>
                  </div>
                  <h3 className="text-sm font-medium text-base-content/70 mb-1">
                    No hay alertas con este filtro
                  </h3>
                  <p className="text-xs text-base-content/60">
                    Intenta seleccionar otro estado
                  </p>
                </div>
              </div>
            ) : (
              alertasFiltradas.map((alerta, index) => (
                <div
                  key={`${alerta.alertaKey}-${index}`}
                  className="border border-base-300 rounded-lg p-3 hover:bg-base-200/50 transition-colors"
                >
                  {/* Fila 1: Estado y Tipo */}
                  <div className="flex items-start justify-between gap-2 mb-2">
                    {getSemaforoIndicator(alerta.semaforo)}
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="badge badge-ghost badge-xs">
                          {alerta.etapa}
                        </span>
                        <span className="badge badge-outline badge-xs">
                          {getTipoLabel(alerta.tipo)}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-base-content/90 line-clamp-2">
                        {alerta.accion_requerida}
                      </p>
                    </div>
                  </div>

                  {/* Fila 2: Barra de progreso */}
                  <div className="mb-2">
                    {getMiniProgressBar(alerta.semaforo)}
                  </div>

                  {/* Fila 3: Info adicional */}
                  <div className="flex items-center justify-between text-xs text-base-content/50">
                    <div className="flex items-center gap-3">
                      <span className="flex items-center gap-1">
                        <svg
                          className="w-3 h-3"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                          />
                        </svg>
                        {alerta.plazo_legal}
                      </span>
                      <span className="flex items-center gap-1">
                        <svg
                          className="w-3 h-3"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                          />
                        </svg>
                        Límite: {formatFecha(alerta.fecha_limite)}
                      </span>
                    </div>
                    <span
                      className={`font-semibold ${
                        alerta.semaforo.urgencia === "critico"
                          ? "text-error"
                          : alerta.semaforo.urgencia === "alta"
                          ? "text-error"
                          : alerta.semaforo.urgencia === "media"
                          ? "text-warning"
                          : "text-success"
                      }`}
                    >
                      {alerta.semaforo.dias_transcurridos}d /{" "}
                      {alerta.semaforo.dias_totales}d
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {/* Footer con tooltip explicativo - solo si hay alertas */}
        {alertasFlat.length > 0 && (
          <div className="mt-3 pt-3 border-t border-base-300">
            <div className="flex items-center justify-between text-xs text-base-content/50">
              <div className="flex items-center gap-1">
                <svg
                  className="w-3 h-3"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                    clipRule="evenodd"
                  />
                </svg>
                <span>Semaforización de plazos legales</span>
              </div>
              <span className="font-mono">
                {alertasFiltradas.length} de {alertasFlat.length}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
