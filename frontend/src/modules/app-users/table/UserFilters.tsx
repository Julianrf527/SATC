import CustomSelect from "@shared/ui/form/CustomSelect";
import type { RolResumen } from "../types";
import { hayFiltrosActivos, type FiltrosUsuarios } from "./filtrosUsuarios";

type Props = {
  value: FiltrosUsuarios;
  onChange: (value: FiltrosUsuarios) => void;
  onClear: () => void;
  rolList: RolResumen[];
};

/** Card de filtros de la gestión de usuarios. */
export default function UserFilters({ value, onChange, onClear, rolList }: Props) {
  const hasActiveFilters = hayFiltrosActivos(value);
  const set = (campo: keyof FiltrosUsuarios, v: string) => onChange({ ...value, [campo]: v });

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-base-content/70 flex items-center gap-2">
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
                d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z"
              />
            </svg>
            Filtros de búsqueda
            {hasActiveFilters && (
              <span className="badge badge-primary badge-sm">
                activos
              </span>
            )}
          </span>
          <button
            onClick={onClear}
            disabled={!hasActiveFilters}
            className={`btn btn-xs gap-1 ${hasActiveFilters ? "btn-error btn-outline" : "btn-ghost opacity-40"}`}
          >
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
            Limpiar
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="flex flex-col">
            <label className="label py-1">
              <span className="text-base-content text-xs">Cédula</span>
            </label>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm"
              value={value.documento}
              onChange={(e) => set("documento", e.target.value)}
            />
          </div>
          <div className="flex flex-col">
            <label className="label py-1">
              <span className="text-base-content text-xs">Nombre</span>
            </label>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm"
              value={value.nombre}
              onChange={(e) => set("nombre", e.target.value)}
            />
          </div>
          <div className="flex flex-col">
            <label className="label py-1">
              <span className="text-base-content text-xs">Correo</span>
            </label>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm"
              value={value.correo}
              onChange={(e) => set("correo", e.target.value)}
            />
          </div>
          <div className="flex flex-col">
            <label className="label py-1">
              <span className="text-base-content text-xs">Rol</span>
            </label>
            <CustomSelect
              className="select-sm"
              hidePlaceholderOption
              value={value.rol}
              onChange={(v) => set("rol", v)}
              options={[
                { value: "all", label: "Todos" },
                ...rolList.map((r) => ({ value: String(r.id), label: r.nombre })),
              ]}
            />
          </div>
          <div className="flex flex-col">
            <label className="label py-1">
              <span className="text-base-content text-xs">Estado</span>
            </label>
            <CustomSelect
              className="select-sm"
              hidePlaceholderOption
              value={value.estado}
              onChange={(v) => set("estado", v)}
              options={[
                { value: "all", label: "Todos" },
                { value: "active", label: "Activos" },
                { value: "inactive", label: "Inactivos" },
              ]}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
