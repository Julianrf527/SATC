import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { Alerta, EstadoSemaforo, SetToast } from "./types";
import { TIPO_LABELS, URGENCIA_ORDER, formatFechaCorta } from "./alertasConfig";
import { useAlertasTodasQuery, useErrorToast } from "./api/alertas";
import {
  ALCANCE_OPCIONES,
  destinoAlerta,
  endpointConAlcance,
  type AlcanceAlertas,
  type RutasAlertas,
} from "./alertasAlcance";

type AlertaFlat = {
  radicado: string;
  alertaKey: string;
} & Alerta;

type Props = {
  alertsAllEndpoint: string;
  /** Destino del enlace: Gestionar (expediente propio) o Consultar (ajeno). */
  rutas: RutasAlertas;
  processName: string;
  setToast: SetToast;
};

const SEMAFORO_BADGE: Record<EstadoSemaforo, { cls: string; label: string; emoji: string }> = {
  verde:    { cls: "badge-success", label: "Verde",    emoji: "🟢" },
  amarillo: { cls: "badge-warning", label: "Amarillo", emoji: "🟡" },
  rojo:     { cls: "badge-error",   label: "Rojo",     emoji: "🔴" },
  vencido:  { cls: "badge-error opacity-80", label: "Vencido", emoji: "⚫" },
};

const CONTADORES: { key: EstadoSemaforo; label: string; dot: string; text: string }[] = [
  { key: "verde", label: "Verde", dot: "bg-success", text: "text-success" },
  { key: "amarillo", label: "Amarillo", dot: "bg-warning", text: "text-tono-warning" },
  { key: "rojo", label: "Rojo", dot: "bg-error", text: "text-error" },
  { key: "vencido", label: "Vencido", dot: "bg-neutral", text: "text-base-content" },
];

export default function AlertasExpediente({
  alertsAllEndpoint,
  rutas,
  processName,
  setToast,
}: Props) {
  const navigate = useNavigate();
  const [alcance, setAlcance] = useState<AlcanceAlertas>("mios");
  const { data, isPending: isLoading, error } = useAlertasTodasQuery(
    endpointConAlcance(alertsAllEndpoint, alcance),
  );
  useErrorToast(error, setToast, "Error al cargar alertas");
  const [radicadoFilter, setRadicadoFilter] = useState("");
  const [estadoFilter, setEstadoFilter] = useState("all");
  const [tipoFilter, setTipoFilter] = useState("all");
  const [page, setPage] = useState(1);
  const rowsPerPage = 10;

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

  useEffect(() => setPage(1), [radicadoFilter, estadoFilter, tipoFilter, alcance]);

  const formatFecha = (f: string) => formatFechaCorta(f, true);

  const hayFiltrosActivos = !!radicadoFilter.trim() || estadoFilter !== "all" || tipoFilter !== "all";
  const limpiarFiltros = () => {
    setRadicadoFilter("");
    setEstadoFilter("all");
    setTipoFilter("all");
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
                <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                  {processName}
                </p>
                <h1 className="text-lg font-bold text-base-content">Sistema de Alertas</h1>
              </div>
            </div>

            {!isLoading && (
              <div className="flex items-center gap-2 flex-wrap" aria-label="Alertas por estado">
                {CONTADORES.map(({ key, label, dot, text }) => (
                  <span
                    key={key}
                    title={label}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-base-100 border border-base-300 text-xs"
                  >
                    <span className={`w-2 h-2 rounded-full ${dot}`} />
                    <span className={`font-bold ${text}`}>{stats[key]}</span>
                    <span className="text-base-content/60">{label}</span>
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Body: un recuadro con los filtros y otro con la tabla (como asignar encargados) */}
      <div className="w-full min-h-[calc(100vh-5rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-7xl mx-auto space-y-4">
          <div className="card bg-base-100 shadow border border-base-300">
            <div className="card-body p-4">
              <div className="grid grid-cols-1 md:grid-cols-[repeat(4,minmax(0,1fr))_auto] gap-3 items-end">
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Expedientes</span>
                  <div className="join w-full" role="group" aria-label="Alcance de las alertas">
                    {ALCANCE_OPCIONES.map(({ value, label }) => (
                      <button
                        key={value}
                        type="button"
                        aria-pressed={alcance === value}
                        className={`join-item btn btn-sm flex-1 ${alcance === value ? "btn-warning" : "btn-ghost border-base-300"}`}
                        onClick={() => setAlcance(value)}
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Radicado</span>
                  <input className="input input-sm w-full"
                    placeholder="Buscar por radicado..."
                    value={radicadoFilter}
                    onChange={(e) => setRadicadoFilter(e.target.value)} />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Estado</span>
                  <CustomSelect
                    className="select-sm"
                    hidePlaceholderOption
                    value={estadoFilter}
                    onChange={setEstadoFilter}
                    options={[
                      { value: "all", label: "Todos los estados" },
                      { value: "verde", label: "🟢 Verde" },
                      { value: "amarillo", label: "🟡 Amarillo" },
                      { value: "rojo", label: "🔴 Rojo" },
                      { value: "vencido", label: "⚫ Vencido" },
                    ]}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Tipo de alerta</span>
                  <CustomSelect
                    className="select-sm"
                    hidePlaceholderOption
                    value={tipoFilter}
                    onChange={setTipoFilter}
                    options={[
                      { value: "all", label: "Todos los tipos" },
                      ...tiposUnicos.map((t) => ({ value: t, label: TIPO_LABELS[t] ?? t })),
                    ]}
                  />
                </div>
                <button
                  type="button"
                  className="btn btn-sm btn-ghost"
                  disabled={!hayFiltrosActivos}
                  onClick={limpiarFiltros}
                >
                  Limpiar filtros
                </button>
              </div>
            </div>
          </div>

          <div className="card bg-base-100 shadow border border-base-300">
            <div className="card-body p-4">
              {isLoading ? (
                <div className="flex justify-center items-center py-16">
                  <span className="loading loading-spinner loading-lg text-tono-warning" />
                  <p className="ml-4 text-base-content/60">Cargando alertas...</p>
                </div>
              ) : (
                <>
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
                                <span className="text-base-content/60 font-medium">
                                  {alertasFlat.length === 0 ? "¡Todo al día! Sin alertas." : "Sin resultados con los filtros aplicados"}
                                </span>
                              </div>
                            </td>
                          </tr>
                        ) : (
                          paginatedData.map((alerta, idx) => {
                            const badge = SEMAFORO_BADGE[alerta.semaforo.estado];
                            const destino = destinoAlerta(alerta, rutas);
                            return (
                              <tr key={`${alerta.radicado}-${alerta.alertaKey}-${idx}`} className="hover">
                                <td>
                                  <div className="flex flex-col items-center gap-0.5">
                                    <span className={`badge ${badge.cls} badge-sm text-white gap-1`}>
                                      {badge.emoji} {badge.label}
                                    </span>
                                    <span className="text-[10px] text-base-content/60 font-mono">
                                      {alerta.semaforo.porcentaje_avance.toFixed(0)}%
                                    </span>
                                  </div>
                                </td>
                                <td>
                                  <div className="flex flex-col items-start gap-0.5">
                                    <span className="font-mono text-xs font-semibold">{alerta.radicado}</span>
                                    {alcance === "todos" && (
                                      alerta.es_responsable === false ? (
                                        <span className="text-[10px] text-base-content/60">Otro responsable</span>
                                      ) : (
                                        <span className="badge badge-warning badge-outline badge-xs">Mío</span>
                                      )
                                    )}
                                  </div>
                                </td>
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
                                    <div className="flex justify-between text-[10px] text-base-content/60">
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
                                    className={`btn btn-xs gap-1 ${destino.accion === "Gestionar" ? "btn-success text-white" : "btn-outline btn-info"}`}
                                    title={destino.accion === "Gestionar"
                                      ? "Expediente a su cargo"
                                      : "Expediente de otro responsable (solo lectura)"}
                                    onClick={() => navigate(destino.ruta, {
                                      state: { radicadoToSelect: alerta.radicado, timestamp: Date.now() }
                                    })}
                                  >
                                    <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                        d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                    </svg>
                                    {destino.accion}
                                  </button>
                                </td>
                              </tr>
                            );
                          })
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Paginación (mismo formato que asignar encargados) */}
                  <div className="flex justify-between items-center pt-4 border-t border-base-300 mt-4">
                    <div className="text-sm text-base-content/60">
                      Mostrando {paginatedData.length} de {alertasFiltradas.length} alerta{alertasFiltradas.length !== 1 ? "s" : ""}
                    </div>
                    <div className="join">
                      <button
                        className="join-item btn btn-sm"
                        aria-label="Página anterior"
                        disabled={page === 1 || alertasFiltradas.length === 0}
                        onClick={() => setPage(page - 1)}
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                        </svg>
                      </button>
                      <button className="join-item btn btn-sm no-animation">
                        Página {alertasFiltradas.length === 0 ? 0 : page} de {totalPages}
                      </button>
                      <button
                        className="join-item btn btn-sm"
                        aria-label="Página siguiente"
                        disabled={page >= totalPages || alertasFiltradas.length === 0}
                        onClick={() => setPage(page + 1)}
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
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
