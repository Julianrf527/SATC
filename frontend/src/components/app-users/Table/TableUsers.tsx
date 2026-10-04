import { useState, useEffect, useRef } from "react";

type Rol = { id: number; nombre: string };

type UserRow = {
  id: number;
  document: number;
  name: string;
  email: string;
  rol_id: number;
  state: boolean;
  primer_nombre: string;
  segundo_nombre: string | null;
  primer_apellido: string;
  segundo_apellido: string | null;
};

type Props = {
  titles: string[];
  data: UserRow[];
  rolList: Rol[];
  onEdit: (user: UserRow) => void;
  onResendPassword: (user: UserRow) => void;
};

export default function TableUsers({ titles, data, rolList, onEdit, onResendPassword }: Props) {
  const [page, setPage] = useState(1);
  const rowsPerPage = 10;
  const paginatedData = data.slice((page - 1) * rowsPerPage, page * rowsPerPage);
  const totalPages = Math.max(1, Math.ceil(data.length / rowsPerPage));

  const prevDataLength = useRef(data.length);
  useEffect(() => {
    if (data.length !== prevDataLength.current) {
      setPage(1);
      prevDataLength.current = data.length;
    }
  }, [data.length]);

  const rolNombre = (rolId: number) =>
    rolList.find((r) => r.id === rolId)?.nombre ?? "—";

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
            {paginatedData.length === 0 ? (
              <tr>
                <td colSpan={titles.length} className="text-center py-12">
                  <div className="flex flex-col items-center gap-2">
                    <svg className="w-12 h-12 text-base-content/30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                    </svg>
                    <span className="text-base-content/60 font-medium">No hay usuarios</span>
                    <span className="text-base-content/40 text-sm">Intenta ajustar los filtros</span>
                  </div>
                </td>
              </tr>
            ) : (
              paginatedData.map((user) => (
                <tr key={user.id} className="hover">
                  <td className="select-text font-mono text-sm w-[12%]">{user.document}</td>
                  <td className="select-text w-[22%]">{user.name}</td>
                  <td className="select-text w-[22%]">{user.email}</td>
                  <td className="w-[15%]">{rolNombre(user.rol_id)}</td>
                  <td className="w-[13%]">
                    <span className={`badge badge-sm ${user.state ? "badge-success" : "badge-ghost"}`}>
                      {user.state ? "Activo" : "Inactivo"}
                    </span>
                  </td>
                  <td className="w-[20%]">
                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() => onEdit(user)}
                        className="btn btn-xs btn-success text-white gap-1"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                        Editar
                      </button>
                      <button
                        onClick={() => onResendPassword(user)}
                        className="btn btn-xs btn-warning text-white gap-1"
                        title="Reenviar contraseña"
                      >
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        Reenviar
                      </button>
                    </div>
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
          Mostrando {paginatedData.length} de {data.length} usuario{data.length !== 1 ? "s" : ""}
        </div>
        <div className="join">
          <button className="join-item btn btn-sm" disabled={page === 1} onClick={() => setPage(page - 1)}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <button className="join-item btn btn-sm no-animation">
            Página {data.length === 0 ? 0 : page} de {totalPages}
          </button>
          <button className="join-item btn btn-sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
