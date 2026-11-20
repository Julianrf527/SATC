import { Filter, RefreshCw, X } from "lucide-react";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { OpcionFiltro } from "../../types";
import { FILTROS_MIS_ACTUACIONES, type FiltrosMisActuaciones } from "./filtros";

type Props = {
  filtros: FiltrosMisActuaciones;
  onChange: (f: FiltrosMisActuaciones) => void;
  /** Tipos y roles del usuario (vienen del backend). */
  tipos: OpcionFiltro[];
  roles: OpcionFiltro[];
  /** Estados presentes en la lista. */
  opcionesEstado: { value: string; label: string }[];
  onActualizar: () => void;
  actualizando: boolean;
};

const TODOS = { value: "all", label: "Todos" };

export default function MisActuacionesFiltros({
  filtros,
  onChange,
  tipos,
  roles,
  opcionesEstado,
  onActualizar,
  actualizando,
}: Props) {
  const activos =
    filtros.radicado !== "" || filtros.tipo !== "all" || filtros.rol !== "all" || filtros.estado !== "all" || filtros.soloMiTurno;
  const set = (parcial: Partial<FiltrosMisActuaciones>) => onChange({ ...filtros, ...parcial });

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-base-content/70 flex items-center gap-2">
            <Filter size={14} />
            Filtros de búsqueda
            {activos && <span className="badge badge-success badge-sm">activos</span>}
          </span>
          <div className="flex items-center gap-2">
            <button type="button" onClick={onActualizar} className="btn btn-ghost btn-xs gap-1" disabled={actualizando}>
              <RefreshCw size={12} className={actualizando ? "animate-spin" : ""} />
              Actualizar
            </button>
            <button
              type="button"
              onClick={() => onChange(FILTROS_MIS_ACTUACIONES)}
              disabled={!activos}
              className={`btn btn-xs gap-1 ${activos ? "btn-error btn-outline" : "btn-ghost opacity-40"}`}
            >
              <X size={12} />
              Limpiar
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Radicado</span>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm w-full"
              value={filtros.radicado}
              onChange={(e) => set({ radicado: e.target.value })}
            />
          </label>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Documento</span>
            <CustomSelect
              className="select-sm"
              value={filtros.tipo}
              onChange={(tipo) => set({ tipo })}
              hidePlaceholderOption
              options={[TODOS, ...tipos.map((t) => ({ value: t.codigo, label: t.etiqueta }))]}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Mi rol</span>
            <CustomSelect
              className="select-sm"
              value={filtros.rol}
              onChange={(rol) => set({ rol })}
              hidePlaceholderOption
              options={[TODOS, ...roles.map((r) => ({ value: r.codigo, label: r.etiqueta }))]}
            />
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium text-base-content/60">Estado</span>
            <CustomSelect
              className="select-sm"
              value={filtros.estado}
              onChange={(estado) => set({ estado })}
              hidePlaceholderOption
              options={[TODOS, ...opcionesEstado]}
            />
          </div>
          <label className="flex items-center gap-2 self-end pb-1 cursor-pointer">
            <input
              type="checkbox"
              className="checkbox checkbox-sm checkbox-info"
              checked={filtros.soloMiTurno}
              onChange={(e) => set({ soloMiTurno: e.target.checked })}
            />
            <span className="text-xs font-medium text-base-content/70">Solo los que requieren mi acción</span>
          </label>
        </div>
      </div>
    </div>
  );
}
