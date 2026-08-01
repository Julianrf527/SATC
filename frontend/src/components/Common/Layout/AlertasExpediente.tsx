import { useEffect, useMemo, useState } from "react";
import { apiCall } from "../../../utils/api";
import { useNavigate } from "react-router-dom";

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
  fecha_limite: string;
  semaforo: Semaforo;
};

type AlertaFlat = {
  radicado: string;
  alertaKey: string;
} & Alerta;

type ResponseAlertas = {
  ok: boolean;
  alertas: Record<string, Record<string, Alerta>>;
  total_expedientes: number;
  expedientes_con_alertas: number;
  estadisticas_semaforo: { verde: number; amarillo: number; rojo: number; vencido: number };
};

type Props = {
  alertsAllEndpoint: string;
  navigatePath: string;
  processName: string;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

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

const SEMAFORO_BADGE: Record<EstadoSemaforo, { cls: string; label: string; emoji: string }> = {
  verde:    { cls: "badge-success", label: "Verde",    emoji: "🟢" },
  amarillo: { cls: "badge-warning", label: "Amarillo", emoji: "🟡" },
  rojo:     { cls: "badge-error",   label: "Rojo",     emoji: "🔴" },
  vencido:  { cls: "badge-error opacity-80", label: "Vencido", emoji: "⚫" },
};

export default function AlertasExpediente({
  alertsAllEndpoint,
  navigatePath,
  processName,
  setToast,
}: Props) {
  const navigate = useNavigate();
  const [data, setData] = useState<ResponseAlertas | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [radicadoFilter, setRadicadoFilter] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("all");
  const [tipoFilter, setTipoFilter] = useState("all");
  const [page, setPage] = useState(1);
  const rowsPerPage = 10;

  useEffect(() => { loadAlertas(); }, [alertsAllEndpoint]);

  const loadAlertas = async () => {
    try {
      setIsLoading(true);
      const res = await apiCall(alertsAllEndpoint, { method: "GET" });
      if (res.ok) setData(res);
      else setToast({ id: Date.now(), message: res.detail || "Error al cargar alertas", type: "error" });
    } catch {
      setToast({ id: Date.now(), message: "Error al cargar las alertas", type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const alertasFlat = useMemo<AlertaFlat[]>(() => {
    if (!data) return [];
    const flat: AlertaFlat[] = [];
    Object.entries(data.alertas).forEach(([radicado, alertasExp]) => {
      Object.entries(alertasExp).forEach(([alertaKey, alerta]) => {
        flat.push({ radicado, alertaKey, ...alerta });
      });
    });
    return flat;
  }, [data]);

  const tiposUnicos = useMemo(() => Array.from(new Set(alertasFlat.map((a) => a.tipo))).sort(), [alertasFlat]);

  const URGENCIA_ORDER: Record<string, number> = { critico: 0, alta: 1, media: 2, baja: 3 };

  const alertasFiltradas = useMemo(() => {
    const rad = radicadoFilter.trim().toLowerCase();
    return alertasFlat
      .filter((a) => {
        const mRad = rad ? a.radicado.toLowerCase().includes(rad) : true;
        const mEst = estadoFilter === "all" || a.semaforo.estado === estadoFilter;
        const mTip = tipoFilter === "all" || a.tipo === tipoFilter;
        return mRad && mEst && mTip;
      })
      .sort((a, b) => {
        const diff = URGENCIA_ORDER[a.semaforo.urgencia] - URGENCIA_ORDER[b.semaforo.urgencia];
        return diff !== 0 ? diff : b.semaforo.porcentaje_avance - a.semaforo.porcentaje_avance;
      });
  }, [alertasFlat, radicadoFilter, estadoFilter, tipoFilter]);

  const totalPages = Math.max(1, Math.ceil(alertasFiltradas.length / rowsPerPage));
  const paginatedData = alertasFiltradas.slice((page - 1) * rowsPerPage, page * rowsPerPage);

  useEffect(() => setPage(1), [radicadoFilter, estadoFilter, tipoFilter]);

  const formatFecha = (f: string) => {
    try { return new Date(f).toLocaleDateString("es-CO", { year: "numeric", month: "short", day: "numeric" }); }
    catch { return f; }
  };

  const stats = data?.estadisticas_semaforo ?? { verde: 0, amarillo: 0, rojo: 0, vencido: 0 };

  return (
    <>
      {/* Header al estilo SignUpLayout */}
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-warning/10 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                  {processName}
                </p>
                <h1 className="text-lg font-bold text-base-content">Sistema de Alertas</h1>
              </div>
            </div>

            {!isLoading && (
              <div className="flex items-center gap-3 flex-wrap">
                {[
                  { key: "verde",    label: "Verde",    cls: "text-success", bg: "bg-success/10",  border: "border-success/30",  emoji: "🟢" },
                  { key: "amarillo", label: "Amarillo", cls: "text-warning", bg: "bg-warning/10",  border: "border-warning/30",  emoji: "🟡" },
                  { key: "rojo",     label: "Rojo",     cls: "text-error",   bg: "bg-error/10",    border: "border-error/30",    emoji: "🔴" },
                  { key: "vencido",  label: "Vencido",  cls: "text-error",   bg: "bg-error/5",     border: "border-error/20",    emoji: "⚫" },
                ].map(({ key, label, cls, bg, border, emoji }) => (
                  <div key={key}
                    className={`flex flex-col items-center px-4 py-2 ${bg} border ${border} rounded-xl min-w-[5rem]`}>
                    <span className="text-lg">{emoji}</span>
                    <span className={`text-2xl font-bold leading-tight ${cls}`}>
                      {stats[key as EstadoSemaforo]}
                    </span>
                    <span className="text-xs text-base-content/50">{label}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="w-full min-h-[calc(100vh-5rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-7xl mx-auto">
          <div className="card bg-base-100 shadow border border-base-300">
            <div className="card-body p-5 flex flex-col gap-4">

              {isLoading ? (
                <div className="flex justify-center items-center py-16">
                  <span className="loading loading-spinner loading-lg text-warning" />
                  <p className="ml-4 text-base-content/60">Cargando alertas...</p>
                </div>
              ) : (
                <>
                  {/* Filtros */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <div className="flex flex-col gap-1">
                      <span className="text-xs font-medium text-base-content/60">Radicado</span>
                      <input className="input input-sm input-bordered w-full"
                        placeholder="Buscar por radicado..."
                        value={radicadoFilter}
                        onChange={(e) => setRadicadoFilter(e.target.value)} />
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-xs font-medium text-base-content/60">Estado</span>
                      <select className="select select-sm select-bordered w-full"
                        value={estadoFilter} onChange={(e) => setEstadoFilter(e.target.value)}>
                        <option value="all">Todos los estados</option>
                        <option value="verde">🟢 Verde</option>
                        <option value="amarillo">🟡 Amarillo</option>
                        <option value="rojo">🔴 Rojo</option>
                        <option value="vencido">⚫ Vencido</option>
                      </select>
                    </div>
                    <div className="flex flex-col gap-1">
                      <span className="text-xs font-medium text-base-content/60">Tipo de alerta</span>
                      <select className="select select-sm select-bordered w-full"
                        value={tipoFilter} onChange={(e) => setTipoFilter(e.target.value)}>
                        <option value="all">Todos los tipos</option>
                        {tiposUnicos.map((t) => (
                          <option key={t} value={t}>{TIPO_LABELS[t] ?? t}</option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Tabla */}
                  <div className="overflow-x-auto border border-base-300 rounded-lg">
                    <table className="table table-sm w-full">
                      <thead className="bg-base-200">
                        <tr>
                          <th className="text-xs">Estado</th>
                          <th className="text-xs">Radicado</th>
                          <th className="text-xs">Etapa / Tipo</th>
                          <th className="text-xs">Acción requerida</th>
                          <th className="text-xs w-48">Progreso</th>
                          <th className="text-xs">Fecha límite</th>
                          <th className="text-xs text-center">Acción</th>
                        </tr>
                      </thead>
                      <tbody>
                        {paginatedData.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="text-center py-10">
                              <div className="flex flex-col items-center gap-2">
                                <svg className="w-10 h-10 text-base-content/20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                <span className="text-base-content/50 font-medium">
                                  {alertasFlat.length === 0 ? "¡Todo al día! Sin alertas." : "Sin resultados con los filtros aplicados"}
                                </span>
                              </div>
                            </td>
                          </tr>
                        ) : (
                          paginatedData.map((alerta, idx) => {
                            const badge = SEMAFORO_BADGE[alerta.semaforo.estado];
                            return (
                              <tr key={`${alerta.radicado}-${alerta.alertaKey}-${idx}`} className="hover">
                                <td>
                                  <div className="flex flex-col items-center gap-0.5">
                                    <span className={`badge ${badge.cls} badge-sm text-white gap-1`}>
                                      {badge.emoji} {badge.label}
                                    </span>
                                    <span className="text-[10px] text-base-content/50 font-mono">
                                      {alerta.semaforo.porcentaje_avance.toFixed(0)}%
                                    </span>
                                  </div>
                                </td>
                                <td className="font-mono text-xs font-semibold">{alerta.radicado}</td>
                                <td>
                                  <div className="flex flex-col gap-1">
                                    <span className="badge badge-ghost badge-xs">{alerta.etapa}</span>
                                    <span className="badge badge-outline badge-xs">
                                      {TIPO_LABELS[alerta.tipo] ?? alerta.tipo}
                                    </span>
                                  </div>
                                </td>
                                <td className="text-xs max-w-[12rem]">
                                  <p className="line-clamp-2">{alerta.accion_requerida}</p>
                                </td>
                                <td className="w-48">
                                  <div className="flex flex-col gap-1">
                                    <div className="w-full bg-base-300 rounded-full h-1.5 overflow-hidden">
                                      <div className="h-1.5 rounded-full"
                                        style={{
                                          width: `${Math.min(alerta.semaforo.porcentaje_avance, 100)}%`,
                                          backgroundColor: alerta.semaforo.color_hex,
                                        }} />
                                    </div>
                                    <div className="flex justify-between text-[10px] text-base-content/50">
                                      <span>{alerta.semaforo.dias_transcurridos}d</span>
                                      <span>
                                        {alerta.semaforo.esta_vencido
                                          ? <span className="text-error font-semibold">Vencido</span>
                                          : `${alerta.semaforo.dias_restantes}d restantes`}
                                      </span>
                                    </div>
                                  </div>
                                </td>
                                <td className="text-xs">
                                  <div className="flex flex-col">
                                    <span className="font-semibold">{formatFecha(alerta.fecha_limite)}</span>
                                    {alerta.semaforo.esta_vencido && (
                                      <span className="text-error text-[10px] font-semibold">¡Vencido!</span>
                                    )}
                                  </div>
                                </td>
                                <td>
                                  <button
                                    className="btn btn-success btn-xs text-white gap-1"
                                    onClick={() => navigate(navigatePath, {
                                      state: { radicadoToSelect: alerta.radicado, timestamp: Date.now() }
                                    })}
                                  >
                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                    </svg>
                                    Gestionar
                                  </button>
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Paginación */}
                  <div className="flex justify-between items-center pt-2">
                    <span className="text-xs text-base-content/50">
                      {paginatedData.length} de {alertasFiltradas.length} alerta{alertasFiltradas.length !== 1 ? "s" : ""}
                    </span>
                    <div className="join">
                      <button className="join-item btn btn-sm btn-ghost"
                        disabled={page === 1} onClick={() => setPage(page - 1)}>«</button>
                      <button className="join-item btn btn-sm no-animation btn-ghost">
                        {alertasFiltradas.length === 0 ? 0 : page} / {totalPages}
                      </button>
                      <button className="join-item btn btn-sm btn-ghost"
                        disabled={page >= totalPages} onClick={() => setPage(page + 1)}>»</button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
