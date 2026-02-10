type Involved = {
  id: number;
  numero_documento: number;
  digito_verificacion: string | null;
  tipo_documento: string;
  nombre: string;
  celular: number;
  correo: string;
};

type Props = {
  titles: string[];
  data: Involved[];
  page: number;
  totalPages: number;
  loading: boolean;
  onPageChange: (page: number) => void;
  onEdit: (involved: Involved) => void;
  // Filtros
  numeroDocumentoFilter: string;
  tipoDocumentoFilter: string;
  nombreFilter: string;
  correoFilter: string;
  onNumeroDocumentoFilterChange: (value: string) => void;
  onTipoDocumentoFilterChange: (value: string) => void;
  onNombreFilterChange: (value: string) => void;
  onCorreoFilterChange: (value: string) => void;
};

export default function TableInvolved({
  titles,
  data,
  page,
  totalPages,
  loading,
  onPageChange,
  onEdit,
  numeroDocumentoFilter,
  tipoDocumentoFilter,
  nombreFilter,
  correoFilter,
  onNumeroDocumentoFilterChange,
  onTipoDocumentoFilterChange,
  onNombreFilterChange,
  onCorreoFilterChange,
}: Props) {
  const handleClearFilters = () => {
    onNumeroDocumentoFilterChange("");
    onTipoDocumentoFilterChange("");
    onNombreFilterChange("");
    onCorreoFilterChange("");
  };

  const hasActiveFilters =
    numeroDocumentoFilter ||
    tipoDocumentoFilter ||
    nombreFilter ||
    correoFilter;

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
        <div className="p-4 bg-base-200 rounded-lg grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Número Documento</span>
            </label>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm input-bordered"
              value={numeroDocumentoFilter}
              onChange={(e) => onNumeroDocumentoFilterChange(e.target.value)}
            />
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Tipo Documento</span>
            </label>
            <select
              className="select select-sm select-bordered"
              value={tipoDocumentoFilter}
              onChange={(e) => onTipoDocumentoFilterChange(e.target.value)}
            >
              <option value="">Todos</option>
              <option value="CC">CC</option>
              <option value="CE">CE</option>
              <option value="NIT">NIT</option>
              <option value="TI">TI</option>
              <option value="PAS">PAS</option>
            </select>
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Nombre</span>
            </label>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm input-bordered"
              value={nombreFilter}
              onChange={(e) => onNombreFilterChange(e.target.value)}
            />
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Correo</span>
            </label>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm input-bordered"
              value={correoFilter}
              onChange={(e) => onCorreoFilterChange(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Tabla */}
      <div className="flex-1 overflow-auto border border-base-300 rounded-lg">
        <table className="table table-pin-rows table-xs">
          <thead>
            <tr>
              {titles.map((title, index) => (
                <th key={index} className="bg-base-200">
                  {title}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={titles.length} className="text-center py-8">
                  <span className="loading loading-spinner loading-md"></span>
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={titles.length} className="text-center py-8">
                  No hay involucrados para mostrar
                </td>
              </tr>
            ) : (
              data.map((involved) => (
                <tr key={involved.id} className="hover">
                  <td>
                    {involved.tipo_documento === "NIT" &&
                    involved.digito_verificacion
                      ? `${involved.numero_documento}-${involved.digito_verificacion}`
                      : involved.numero_documento}
                  </td>
                  <td>{involved.tipo_documento}</td>
                  <td>{involved.nombre}</td>
                  <td>{involved.celular}</td>
                  <td className="max-w-xs truncate">{involved.correo}</td>
                  <td>
                    <button
                      onClick={() => onEdit(involved)}
                      className="btn btn-xs btn-success text-white"
                      title="Editar involucrado"
                    >
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-3 w-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                        />
                      </svg>
                      Editar
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      <div className="mt-4 flex justify-between items-center">
        <div className="text-sm text-base-content/70">
          Página {page} de {totalPages}
        </div>
        <div className="join">
          <button
            className="join-item btn btn-sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1 || loading}
          >
            «
          </button>
          <button className="join-item btn btn-sm">Página {page}</button>
          <button
            className="join-item btn btn-sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages || loading}
          >
            »
          </button>
        </div>
      </div>
    </div>
  );
}
