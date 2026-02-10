type Encargado = {
  id: number;
  name: string;
};

export interface Props {
  titles: string[];
  data: Array<{
    radicado: string;
    nombre_expediente: string;
    fecha_creacion: string;
    encargado_id: number | null;
    encargado_nombre?: string;
  }>;
  encargados: Encargado[];
  page: number;
  totalPages: number;
  loading: boolean;
  onPageChange: (newPage: number) => void;
  onChangeEncargado: (radicado: string, encargadoId: number | null) => void;

  radicadoFilter: string;
  expedienteFilter: string;
  fechaFilter: string;
  encargadoFilter: string;
  estadoFilter: string;
  encargadosConExpedientes: Encargado[];

  onRadicadoFilterChange: (v: string) => void;
  onExpedienteFilterChange: (v: string) => void;
  onFechaFilterChange: (v: string) => void;
  onEncargadoFilterChange: (v: string) => void;
  onEstadoFilterChange: (v: string) => void;
}

export default function TableFiles({
  titles,
  data,
  encargados,
  page,
  totalPages,
  loading,
  onPageChange,
  onChangeEncargado,

  radicadoFilter,
  expedienteFilter,
  fechaFilter,
  encargadoFilter,
  estadoFilter,
  onRadicadoFilterChange,
  onExpedienteFilterChange,
  onFechaFilterChange,
  onEncargadoFilterChange,
  onEstadoFilterChange,
}: Props) {
  const safeTotalPages = Math.max(1, totalPages);

  const hasActiveFilters =
    radicadoFilter.trim() !== "" ||
    expedienteFilter.trim() !== "" ||
    fechaFilter.trim() !== "" ||
    encargadoFilter.trim() !== "" ||
    estadoFilter !== "all";

  const handleClearFilters = () => {
    onRadicadoFilterChange("");
    onExpedienteFilterChange("");
    onFechaFilterChange("");
    onEncargadoFilterChange("");
    onEstadoFilterChange("all");
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Panel de filtros - siempre visible */}
      <div className="mb-4">
        <div className="flex justify-between items-center mb-3">
          <h4 className="text-sm font-semibold text-base-content/70">
            Filtros de Búsqueda
          </h4>
          {hasActiveFilters && (
            <button
              onClick={handleClearFilters}
              className="btn btn-xs btn-ghost"
            >
              Limpiar filtros
            </button>
          )}
        </div>
        <div className="p-4 bg-base-200 rounded-lg grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Radicado</span>
            </label>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm input-bordered"
              value={radicadoFilter}
              onChange={(e) => onRadicadoFilterChange(e.target.value)}
            />
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Expediente</span>
            </label>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm input-bordered"
              value={expedienteFilter}
              onChange={(e) => onExpedienteFilterChange(e.target.value)}
            />
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Fecha</span>
            </label>
            <input
              type="date"
              className="input input-sm input-bordered"
              value={fechaFilter}
              onChange={(e) => onFechaFilterChange(e.target.value)}
            />
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Encargado</span>
            </label>
            <input
              type="text"
              placeholder="Nombre o cédula..."
              className="input input-sm input-bordered"
              value={encargadoFilter}
              onChange={(e) => onEncargadoFilterChange(e.target.value)}
            />
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Estado</span>
            </label>
            <select
              className="select select-sm select-bordered"
              value={estadoFilter}
              onChange={(e) => onEstadoFilterChange(e.target.value)}
            >
              <option value="all">Todos</option>
              <option value="asignado">Asignados</option>
              <option value="sin_asignar">Sin asignar</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tabla */}
      <div className="flex-1 overflow-auto border border-base-300 rounded-lg">
        <table className="table table-pin-rows table-xs">
          <thead>
            <tr>
              {titles.map((t, i) => (
                <th key={i} className="bg-base-200">
                  {t}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={titles.length} className="text-center py-8">
                  <div className="flex flex-col items-center gap-2">
                    <span className="loading loading-spinner loading-lg text-success"></span>
                    <span className="text-base-content/60">
                      Cargando datos...
                    </span>
                  </div>
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={titles.length} className="text-center py-12">
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
                        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                      />
                    </svg>
                    <span className="text-base-content/60 font-medium">
                      No hay expedientes
                    </span>
                    <span className="text-base-content/40 text-sm">
                      Intenta ajustar los filtros
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              data.map((f) => (
                <tr key={f.radicado} className="hover">
                  <td className="select-text font-mono text-sm">
                    {f.radicado}
                  </td>
                  <td className="select-text">{f.nombre_expediente}</td>
                  <td className="select-text text-sm">
                    {f.fecha_creacion.split("T")[0]}
                  </td>
                  <td>
                    <select
                      className="select select-bordered select-sm w-full"
                      value={f.encargado_id ?? ""}
                      onChange={(e) =>
                        onChangeEncargado(
                          f.radicado,
                          e.target.value ? Number(e.target.value) : null
                        )
                      }
                    >
                      <option value="">Sin asignar</option>
                      {encargados.map((enc) => (
                        <option key={enc.id} value={enc.id}>
                          {enc.name} (CC: {enc.id})
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    {f.encargado_id ? (
                      <span className="badge badge-success text-white badge-sm gap-1">
                        <svg
                          className="w-3 h-3"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                            clipRule="evenodd"
                          />
                        </svg>
                        Asignado
                      </span>
                    ) : (
                      <span className="badge badge-ghost badge-sm gap-1">
                        <svg
                          className="w-3 h-3"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                            clipRule="evenodd"
                          />
                        </svg>
                        Sin asignar
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      <div className="flex justify-between items-center pt-4 border-t border-base-300 mt-4">
        <div className="text-sm text-base-content/60">
          Mostrando {data.length} expediente{data.length !== 1 ? "s" : ""}
        </div>
        <div className="join">
          <button
            className="join-item btn btn-sm"
            disabled={page === 1 || loading || data.length === 0}
            onClick={() => onPageChange(page - 1)}
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
            Página {data.length === 0 ? 0 : page} de {safeTotalPages}
          </button>
          <button
            className="join-item btn btn-sm"
            disabled={page >= safeTotalPages || loading || data.length === 0}
            onClick={() => onPageChange(page + 1)}
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
  );
}
