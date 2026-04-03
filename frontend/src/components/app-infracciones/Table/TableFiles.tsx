type Encargado = {
  id: number;
  nombre: string;
};

export interface Props {
  titles: string[];
  data: Array<{
    id: number;
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
  selectedIds: Set<number>;
  onSelectionChange: (id: number, checked: boolean) => void;
  onSelectAll: (checked: boolean) => void;
}

export default function TableFiles({
  titles,
  data,
  page,
  totalPages,
  loading,
  onPageChange,
  selectedIds,
  onSelectionChange,
  onSelectAll,
}: Props) {
  const safeTotalPages = Math.max(1, totalPages);
  const allSelected =
    data.length > 0 && data.every((f) => selectedIds.has(f.id));
  const someSelected = data.some((f) => selectedIds.has(f.id));

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Tabla */}
      <div className="flex-1 overflow-auto border border-base-300 rounded-lg">
        <table className="table table-pin-rows table-xs">
          <thead>
            <tr>
              <th className="bg-base-200 w-8">
                <input
                  type="checkbox"
                  className="checkbox checkbox-sm"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = !allSelected && someSelected;
                  }}
                  onChange={(e) => onSelectAll(e.target.checked)}
                  disabled={data.length === 0}
                />
              </th>
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
                <td colSpan={titles.length + 1} className="text-center py-8">
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
                <td colSpan={titles.length + 1} className="text-center py-12">
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
                <tr
                  key={f.id}
                  className={`hover cursor-pointer ${selectedIds.has(f.id) ? "bg-base-200" : ""}`}
                  onClick={() =>
                    onSelectionChange(f.id, !selectedIds.has(f.id))
                  }
                >
                  <td onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      className="checkbox checkbox-sm"
                      checked={selectedIds.has(f.id)}
                      onChange={(e) =>
                        onSelectionChange(f.id, e.target.checked)
                      }
                    />
                  </td>
                  <td className="select-text font-mono text-sm">
                    {f.radicado}
                  </td>
                  <td className="select-text">{f.nombre_expediente}</td>
                  <td className="select-text text-sm">
                    {f.fecha_creacion.split("T")[0]}
                  </td>
                  <td>
                    {f.encargado_nombre ? (
                      <span className="text-sm">{f.encargado_nombre}</span>
                    ) : (
                      <span className="text-base-content/40 text-sm italic">
                        Sin asignar
                      </span>
                    )}
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
          {selectedIds.size > 0 ? (
            <span className="text-success font-medium">
              {selectedIds.size} seleccionado{selectedIds.size !== 1 ? "s" : ""}
            </span>
          ) : (
            <>
              Mostrando {data.length} expediente{data.length !== 1 ? "s" : ""}
            </>
          )}
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
