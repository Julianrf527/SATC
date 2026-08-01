type Involved = {
  id: number;
  numero_documento: number;
  digito_verificacion: string | null;
  tipo_documento: string;
  nombre: string;
  celular: number | null;
  correo: string | null;
  direccion?: string | null;
};

type Props = {
  titles: string[];
  data: Involved[];
  page: number;
  totalPages: number;
  loading: boolean;
  onPageChange: (page: number) => void;
  onEdit: (involved: Involved) => void;
};

export default function TableInvolved({
  titles, data, page, totalPages, loading, onPageChange, onEdit,
}: Props) {
  return (
    <div className="flex flex-col gap-3">
      {/* Tabla */}
      <div className="overflow-auto border border-base-300 rounded-lg">
        <table className="table table-pin-rows table-xs">
          <thead>
            <tr>
              {titles.map((t, i) => <th key={i} className="bg-base-200">{t}</th>)}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={titles.length} className="text-center py-12">
                  <div className="flex flex-col items-center gap-2">
                    <span className="loading loading-spinner loading-md text-secondary" />
                    <span className="text-base-content/60 text-sm">Cargando involucrados...</span>
                  </div>
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={titles.length} className="text-center py-12">
                  <div className="flex flex-col items-center gap-2">
                    <svg className="w-12 h-12 text-base-content/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                    <span className="text-base-content/60 font-medium">No hay involucrados</span>
                    <span className="text-base-content/40 text-sm">Intenta ajustar los filtros</span>
                  </div>
                </td>
              </tr>
            ) : (
              data.map((inv) => (
                <tr key={inv.id} className="hover">
                  <td className="font-mono select-text">
                    {inv.tipo_documento === "NIT" && inv.digito_verificacion
                      ? `${inv.numero_documento}-${inv.digito_verificacion}`
                      : inv.numero_documento}
                  </td>
                  <td>
                    <span className="badge badge-ghost badge-sm">{inv.tipo_documento}</span>
                  </td>
                  <td className="select-text">{inv.nombre}</td>
                  <td className="select-text">{inv.celular ?? ""}</td>
                  <td className="select-text max-w-xs truncate">{inv.correo ?? ""}</td>
                  <td className="select-text max-w-xs truncate">{inv.direccion ?? ""}</td>
                  <td>
                    <button
                      onClick={() => onEdit(inv)}
                      className="btn btn-xs btn-success text-white gap-1"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
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
      <div className="flex justify-between items-center pt-2 border-t border-base-300">
        <div className="text-sm text-base-content/60">
          Página {page} de {totalPages}
        </div>
        <div className="join">
          <button className="join-item btn btn-sm" onClick={() => onPageChange(page - 1)} disabled={page === 1 || loading}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button className="join-item btn btn-sm no-animation">Página {page}</button>
          <button className="join-item btn btn-sm" onClick={() => onPageChange(page + 1)} disabled={page >= totalPages || loading}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
