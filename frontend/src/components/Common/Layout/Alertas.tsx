import { useEffect, useMemo, useState } from "react";
import { apiCall } from "../../../utils/api";

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
  involucrado_nombre?: string;
  accion_requerida: string;
  plazo_legal: string;
  msg: string;
  fecha_inicio?: string;
  fecha_limite: string;
  semaforo: Semaforo;
};

type AlertaFlat = { alertaKey: string } & Alerta;

interface Props {
  expedienteId: number;
  alertEndpoint: string;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
}

const TIPO_LABELS: Record<string, string> = {
  inicio_sancionatorio: "Inicio Sancionatorio",
  decision_fondo: "Decisión de Fondo",
  presentacion_descargos: "Descargos",
  informe_tecnico: "Informe Técnico",
  alegato_conclusion: "Alegato",
  presentacion_recurso: "Recurso",
  resolucion_recurso: "Resolución",
  notificacion_recurso: "Notificación",
  respuesta_plazo: "Plazo Respuesta",
  concepto_constancia: "Constancia Citación",
  concepto_termino: "Término Concepto",
};

const SEMAFORO_CFG = {
  verde:    { emoji: "🟢", textClass: "text-success",        label: "Verde"    },
  amarillo: { emoji: "🟡", textClass: "text-warning",        label: "Amarillo" },
  rojo:     { emoji: "🔴", textClass: "text-error",          label: "Rojo"     },
  vencido:  { emoji: "⚫", textClass: "text-base-content/60", label: "Vencido" },
} as const;

const URGENCIA_ORDER: Record<string, number> = { critico: 0, alta: 1, media: 2, baja: 3 };

const URGENCIA_CLASS: Record<string, string> = {
  critico: "text-error", alta: "text-error", media: "text-warning", baja: "text-success",
};

export default function Alertas({ expedienteId, alertEndpoint, setToast }: Props) {
  const [alertas, setAlertas] = useState<Record<string, Alerta>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadAlertas();
  }, [expedienteId, alertEndpoint]);

  const loadAlertas = async () => {
    try {
      setIsLoading(true);
      const res = await apiCall(alertEndpoint, { method: "GET" });
      if (res.ok) {
        setAlertas(res.alertas || {});
      } else {
        setToast({ id: Date.now(), message: res.detail || "Error al cargar las alertas", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error al cargar las alertas", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const alertasFlat = useMemo<AlertaFlat[]>(() =>
    Object.entries(alertas).map(([alertaKey, a]) => ({ alertaKey, ...a })),
  [alertas]);

  const estadisticas = useMemo(() => {
    const s = { verde: 0, amarillo: 0, rojo: 0, vencido: 0 };
    alertasFlat.forEach((a) => s[a.semaforo.estado]++);
    return s;
  }, [alertasFlat]);

  const alertasOrdenadas = useMemo(() =>
    [...alertasFlat].sort((a, b) => {
      const diff = URGENCIA_ORDER[a.semaforo.urgencia] - URGENCIA_ORDER[b.semaforo.urgencia];
      return diff !== 0 ? diff : b.semaforo.porcentaje_avance - a.semaforo.porcentaje_avance;
    }),
  [alertasFlat]);

  const formatFecha = (f: string) => {
    try { return new Date(f).toLocaleDateString("es-CO", { month: "short", day: "numeric" }); }
    catch { return f; }
  };

  const estadosActivos = (["verde", "amarillo", "rojo", "vencido"] as EstadoSemaforo[])
    .filter((e) => estadisticas[e] > 0);

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-0">
        {/* Header dentro del card */}
        <div className="px-5 py-4 border-b border-base-200 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-warning/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">Plazos Legales</p>
              <h2 className="text-base font-bold text-base-content">Alertas de Plazos</h2>
            </div>
          </div>

          {!isLoading && estadosActivos.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              {estadosActivos.map((estado) => {
                const cfg = SEMAFORO_CFG[estado];
                return (
                  <div key={estado}
                    className="flex flex-col items-center px-2.5 py-1 bg-base-200 rounded-lg min-w-[3rem]">
                    <span className="text-sm leading-none">{cfg.emoji}</span>
                    <span className={`text-lg font-bold leading-tight ${cfg.textClass}`}>{estadisticas[estado]}</span>
                    <span className="text-[9px] text-base-content/50 uppercase">{cfg.label}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Body */}
        <div className="p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <span className="loading loading-spinner loading-md text-warning" />
              <p className="ml-3 text-sm text-base-content/60">Cargando alertas...</p>
            </div>
          ) : alertasFlat.length === 0 ? (
            <div className="text-center py-8">
              <div className="w-12 h-12 bg-base-200 rounded-full flex items-center justify-center mb-3 mx-auto">
                <svg className="w-6 h-6 text-base-content/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-base-content/70">Sin alertas pendientes</p>
              <p className="text-xs text-base-content/50">No hay plazos legales próximos a vencer</p>
            </div>
          ) : (
            <>
              <div className="mb-3">
                <span className="text-xs font-semibold text-base-content/60">
                  {alertasOrdenadas.length} alerta{alertasOrdenadas.length !== 1 ? "s" : ""}
                </span>
              </div>

              <div className="space-y-2">
                {alertasOrdenadas.map((alerta, index) => {
                  const cfg = SEMAFORO_CFG[alerta.semaforo.estado];
                  return (
                    <div key={`${alerta.alertaKey}-${index}`}
                      className="border border-base-300 rounded-lg p-3 hover:bg-base-200/40 transition-colors">
                      <div className="flex items-start gap-3 mb-2">
                        <div className="flex flex-col items-center gap-0.5 pt-0.5 min-w-[2.25rem]">
                          <span className="text-base leading-none">{cfg.emoji}</span>
                          <span className={`text-[9px] font-semibold ${cfg.textClass}`}>{cfg.label}</span>
                          <span className="text-[9px] text-base-content/40 font-mono">
                            {alerta.semaforo.porcentaje_avance.toFixed(0)}%
                          </span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 mb-1 flex-wrap">
                            <span className="badge badge-ghost badge-xs">{alerta.etapa}</span>
                            {alerta.involucrado_nombre ? (
                              <span className="badge badge-outline badge-xs">
                                {alerta.involucrado_nombre}
                              </span>
                            ) : (
                              <span className="badge badge-outline badge-xs">
                                {TIPO_LABELS[alerta.tipo] ?? alerta.tipo}
                              </span>
                            )}
                          </div>
                          <p className="text-sm font-medium text-base-content/90 line-clamp-2">
                            {alerta.accion_requerida}
                          </p>
                        </div>
                        <div className={`text-xs font-bold whitespace-nowrap ${URGENCIA_CLASS[alerta.semaforo.urgencia]}`}>
                          {alerta.semaforo.dias_transcurridos}d / {alerta.semaforo.dias_totales}d
                        </div>
                      </div>

                      {/* Barra progreso */}
                      <div className="flex items-center gap-2 mb-1.5 pl-[2.75rem]">
                        <div className="flex-1 bg-base-300 rounded-full h-1.5 overflow-hidden">
                          <div className="h-1.5 rounded-full transition-all"
                            style={{
                              width: `${Math.min(alerta.semaforo.porcentaje_avance, 100)}%`,
                              backgroundColor: alerta.semaforo.color_hex,
                            }} />
                        </div>
                        <span className="text-xs text-base-content/60 font-mono whitespace-nowrap">
                          {alerta.semaforo.esta_vencido
                            ? <span className="text-error font-bold">¡Vencido!</span>
                            : `${alerta.semaforo.dias_restantes}d`}
                        </span>
                      </div>

                      {/* Meta */}
                      <div className="flex items-center gap-3 text-xs text-base-content/50 pl-[2.75rem]">
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                              d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          {alerta.plazo_legal}
                        </span>
                        <span className="flex items-center gap-1">
                          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                          Límite: {formatFecha(alerta.fecha_limite)}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
