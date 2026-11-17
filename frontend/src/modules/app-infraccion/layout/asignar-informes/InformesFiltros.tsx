import { Filter, RefreshCw, X } from "lucide-react";
import CustomDateInput from "@shared/ui/form/CustomDateInput";
import CustomSelect from "@shared/ui/form/CustomSelect";
import { TIPO_INFORME_OPTIONS, type InformesTecnicosState } from "./useInformesTecnicos";

interface Props {
  state: InformesTecnicosState;
}

export default function InformesFiltros({ state }: Props) {
  const { fetching, profesionales, filtros, setFiltros, refetch, clearFilters, hasActiveFilters } = state;

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-base-content/70 flex items-center gap-2">
            <Filter size={14} />
            Filtros de búsqueda
            {hasActiveFilters && <span className="badge badge-success badge-sm">activos</span>}
          </span>
          <div className="flex items-center gap-2 xl:flex-col xl:items-start xl:gap-0.5">
            <button type="button" onClick={() => refetch()} className="btn btn-ghost btn-xs gap-1" disabled={fetching}>
              <RefreshCw size={12} className={fetching ? "animate-spin" : ""} />
              Actualizar
            </button>
            <button
              type="button"
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
            <CustomDateInput className="input-sm" value={filtros.fechaDesde} onChange={(fechaDesde) => setFiltros({ fechaDesde })} />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Fecha hasta</span>
            <CustomDateInput className="input-sm" value={filtros.fechaHasta} onChange={(fechaHasta) => setFiltros({ fechaHasta })} />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Estado</span>
            <CustomSelect
              className="select-sm"
              value={filtros.aceptado}
              onChange={(v) => setFiltros({ aceptado: v as "" | "true" | "false" })}
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
              value={filtros.profesionalId || 0}
              onChange={(v) => setFiltros({ profesionalId: v === 0 ? "" : v })}
              placeholder="Todos"
              options={profesionales.map((p) => ({ value: p.id, label: p.nombre }))}
            />
          </div>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Radicado</span>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm w-full"
              value={filtros.radicado}
              onChange={(e) => setFiltros({ radicado: e.target.value })}
            />
          </label>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Tipo informe</span>
            <CustomSelect
              className="select-sm"
              value={filtros.tipo}
              onChange={(tipo) => setFiltros({ tipo })}
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
