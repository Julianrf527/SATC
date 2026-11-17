import CustomSelect from "@shared/ui/form/CustomSelect";
import type { UsuarioEncargado } from "./types";

type Props = {
  showExpediente: boolean;
  radicadoFilter: string;
  expedienteFilter: string;
  encargadoFilter: string;
  fechaFilter: string;
  estadoFilter: string;
  onRadicadoFilterChange: (v: string) => void;
  onExpedienteFilterChange: (v: string) => void;
  onEncargadoFilterChange: (v: string) => void;
  onFechaFilterChange: (v: string) => void;
  onEstadoFilterChange: (v: string) => void;
  usuariosDisponibles: UsuarioEncargado[];
  selectedEncargadoId: string;
  onSelectedEncargadoIdChange: (v: string) => void;
  selectedCount: number;
  hayFiltrosActivos: boolean;
  bulkLoading: boolean;
  onLimpiarFiltros: () => void;
  onDeseleccionar: () => void;
  onCambiarEncargado: () => void;
};

/** Filtros del listado + barra de reasignación masiva de encargado. */
export default function EncargadoFiltrosPanel({
  showExpediente,
  radicadoFilter,
  expedienteFilter,
  encargadoFilter,
  fechaFilter,
  estadoFilter,
  onRadicadoFilterChange,
  onExpedienteFilterChange,
  onEncargadoFilterChange,
  onFechaFilterChange,
  onEstadoFilterChange,
  usuariosDisponibles,
  selectedEncargadoId,
  onSelectedEncargadoIdChange,
  selectedCount,
  hayFiltrosActivos,
  bulkLoading,
  onLimpiarFiltros,
  onDeseleccionar,
  onCambiarEncargado,
}: Props) {
  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-4">
        <div className={`grid grid-cols-1 gap-3 mb-3 ${showExpediente ? "md:grid-cols-5" : "md:grid-cols-4"}`}>
          {[
            {
              label: "Radicado",
              value: radicadoFilter,
              onChange: onRadicadoFilterChange,
              type: "text",
              placeholder: "Buscar...",
              show: true,
            },
            {
              label: "Expediente",
              value: expedienteFilter,
              onChange: onExpedienteFilterChange,
              type: "text",
              placeholder: "Buscar...",
              show: showExpediente,
            },
            {
              label: "Encargado",
              value: encargadoFilter,
              onChange: onEncargadoFilterChange,
              type: "text",
              placeholder: "Nombre o cédula",
              show: true,
            },
            {
              label: "Fecha",
              value: fechaFilter,
              onChange: onFechaFilterChange,
              type: "date",
              placeholder: "",
              show: true,
            },
          ].filter((f) => f.show).map(({ label, value, onChange, type, placeholder }) => (
            <div key={label} className="flex flex-col">
              <label className="label">
                <span className="text-base-content text-xs">{label}</span>
              </label>
              <input
                type={type}
                placeholder={placeholder}
                className="input input-sm"
                value={value}
                onChange={(e) => onChange(e.target.value)}
              />
            </div>
          ))}

          <div className="flex flex-col">
            <label className="label">
              <span className="text-base-content text-xs">Estado</span>
            </label>
            <CustomSelect
              className="select-sm"
              hidePlaceholderOption
              value={estadoFilter}
              onChange={onEstadoFilterChange}
              options={[
                { value: "all", label: "Todos" },
                { value: "asignado", label: "Asignados" },
                { value: "sin_asignar", label: "Sin asignar" },
              ]}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 rounded-lg mb-2 items-center">
          <CustomSelect
            className="select-sm h-9"
            value={selectedEncargadoId}
            onChange={onSelectedEncargadoIdChange}
            emptyValue=""
            placeholder="Seleccionar encargado..."
            options={usuariosDisponibles.map((u) => ({
              value: String(u.id),
              label: `${u.nombre} (CC: ${u.numero_documento ?? u.id})`,
            }))}
          />

          <span className="text-sm font-medium text-base-content/80 whitespace-nowrap">
            {selectedCount} seleccionados
          </span>

          <div className="md:col-span-3 flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2">
            <button
              className="btn btn-sm btn-ghost"
              disabled={!hayFiltrosActivos}
              onClick={onLimpiarFiltros}
            >
              Limpiar filtros
            </button>

            <button
              className="btn btn-sm btn-ghost"
              disabled={selectedCount === 0}
              onClick={onDeseleccionar}
            >
              Deseleccionar
            </button>

            <button
              className="btn btn-sm btn-success text-white gap-2"
              onClick={onCambiarEncargado}
              disabled={
                !selectedEncargadoId ||
                bulkLoading ||
                selectedCount === 0
              }
            >
              {bulkLoading ? (
                <span className="loading loading-spinner loading-xs" />
              ) : (
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
                    d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                  />
                </svg>
              )}
              Cambiar Encargado
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
