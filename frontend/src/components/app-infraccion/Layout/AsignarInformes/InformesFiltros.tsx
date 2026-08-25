import { Filter, RefreshCw, X } from "lucide-react";
import {
  TIPO_INFORME_OPTIONS,
  type InformesTecnicosState,
} from "./useInformesTecnicos";
import CustomSelect from "../../../Common/Form/CustomSelect";
import CustomDateInput from "../../../Common/Form/CustomDateInput";

interface Props {
  state: InformesTecnicosState;
}

export default function InformesFiltros({ state }: Props) {
  const {
    loading,
    page,
    setPage,
    profesionales,
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
    clearFilters,
    hasActiveFilters,
  } = state;

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-base-content/70 flex items-center gap-2">
            <Filter size={14} />
            Filtros de búsqueda
            {hasActiveFilters && (
              <span className="badge badge-success badge-sm">activos</span>
            )}
          </span>
          <div className="flex items-center gap-2 xl:flex-col xl:items-start xl:gap-0.5">
            <button
              onClick={() => loadInformes(page)}
              className="btn btn-ghost btn-xs gap-1"
              disabled={loading}
            >
              <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
              Actualizar
            </button>
            <button
              onClick={clearFilters}
              disabled={!hasActiveFilters}
              className={`btn btn-xs gap-1 ${hasActiveFilters ? "btn-error btn-outline" : "btn-ghost opacity-40"}`}
            >
              <X size={12} />
              Limpiar
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Fecha desde</span>
            <CustomDateInput
              className="input-sm"
              value={fechaDesde}
              onChange={(v) => { setFechaDesde(v); setPage(1); }}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Fecha hasta</span>
            <CustomDateInput
              className="input-sm"
              value={fechaHasta}
              onChange={(v) => { setFechaHasta(v); setPage(1); }}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Estado</span>
            <CustomSelect
              className="select-sm"
              value={aceptado}
              onChange={(v) => { setAceptado(v as "" | "true" | "false"); setPage(1); }}
              emptyValue=""
              placeholder="Todos"
              options={[
                { value: "true", label: "Aceptados" },
                { value: "false", label: "Pendientes" },
              ]}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Profesional</span>
            <CustomSelect
              className="select-sm"
              value={profesionalFilter || 0}
              onChange={(v) => { setProfesionalFilter(v === 0 ? "" : v); setPage(1); }}
              placeholder="Todos"
              options={profesionales.map((p) => ({ value: p.id, label: p.nombre }))}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Radicado</span>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm input-bordered w-full"
              value={expedienteRadicadoFilter}
              onChange={(e) => { setExpedienteRadicadoFilter(e.target.value); setPage(1); }}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Tipo informe</span>
            <CustomSelect
              className="select-sm"
              value={tipoInformeFilter}
              onChange={(v) => { setTipoInformeFilter(v); setPage(1); }}
              emptyValue=""
              placeholder="Todos"
              options={TIPO_INFORME_OPTIONS.map((t) => ({ value: t, label: t }))}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
