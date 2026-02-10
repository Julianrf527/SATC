import { useState, useEffect, useRef } from "react";

type Role = {
  id: number;
  name: string;
};

type Props = {
  titles: string[];
  data: {
    id: number;
    name: string;
    email: string;
    rol_id: number;
    state: boolean;
  }[];
  roles: Role[];
  onToggleState: (id: number) => void;
  onToggleRol: (id: number, rol_id: number) => void;

  // filtros
  docFilter: string;
  nameFilter: string;
  emailFilter: string;
  roleFilter: string;
  stateFilter: string;

  onDocFilterChange: (v: string) => void;
  onNameFilterChange: (v: string) => void;
  onEmailFilterChange: (v: string) => void;
  onRoleFilterChange: (v: string) => void;
  onStateFilterChange: (v: string) => void;
};

export default function TableUsers({
  titles,
  data,
  roles,
  onToggleState,
  onToggleRol,
  docFilter,
  nameFilter,
  emailFilter,
  roleFilter,
  stateFilter,
  onDocFilterChange,
  onNameFilterChange,
  onEmailFilterChange,
  onRoleFilterChange,
  onStateFilterChange,
}: Props) {
  const [page, setPage] = useState(1);
  const rowsPerPage = 10;
  const startIndex = (page - 1) * rowsPerPage;
  const endIndex = startIndex + rowsPerPage;
  const paginatedData = data.slice(startIndex, endIndex);
  const totalPages = Math.max(1, Math.ceil(data.length / rowsPerPage));

  // Resetear página cuando cambian los filtros
  const prevDataLength = useRef(data.length);
  useEffect(() => {
    if (data.length !== prevDataLength.current) {
      setPage(1);
      prevDataLength.current = data.length;
    }
  }, [data.length]);

  const hasActiveFilters =
    docFilter.trim() !== "" ||
    nameFilter.trim() !== "" ||
    emailFilter.trim() !== "" ||
    roleFilter !== "all" ||
    stateFilter !== "all";

  const handleClearFilters = () => {
    onDocFilterChange("");
    onNameFilterChange("");
    onEmailFilterChange("");
    onRoleFilterChange("all");
    onStateFilterChange("all");
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
              <span className="label-text text-xs">Cédula</span>
            </label>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm input-bordered"
              value={docFilter}
              onChange={(e) => onDocFilterChange(e.target.value)}
            />
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Nombre</span>
            </label>
            <input
              type="text"
              placeholder="Buscar..."
              className="input input-sm input-bordered"
              value={nameFilter}
              onChange={(e) => onNameFilterChange(e.target.value)}
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
              value={emailFilter}
              onChange={(e) => onEmailFilterChange(e.target.value)}
            />
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Rol</span>
            </label>
            <select
              className="select select-sm select-bordered"
              value={roleFilter}
              onChange={(e) => onRoleFilterChange(e.target.value)}
            >
              <option value="all">Todos</option>
              {roles.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text text-xs">Estado</span>
            </label>
            <select
              className="select select-sm select-bordered"
              value={stateFilter}
              onChange={(e) => onStateFilterChange(e.target.value)}
            >
              <option value="all">Todos</option>
              <option value="active">Activos</option>
              <option value="inactive">Inactivos</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tabla */}
      <div className="flex-1 overflow-auto border border-base-300 rounded-lg">
        <table className="table table-pin-rows table-xs">
          <thead>
            <tr>
              <th className="bg-base-200">{titles[0]}</th>
              <th className="bg-base-200">{titles[1]}</th>
              <th className="bg-base-200">{titles[2]}</th>
              <th className="bg-base-200">{titles[3]}</th>
              <th className="bg-base-200">{titles[4]}</th>
            </tr>
          </thead>
          <tbody>
            {paginatedData.length === 0 ? (
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
                        d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                      />
                    </svg>
                    <span className="text-base-content/60 font-medium">
                      No hay usuarios
                    </span>
                    <span className="text-base-content/40 text-sm">
                      Intenta ajustar los filtros
                    </span>
                  </div>
                </td>
              </tr>
            ) : (
              paginatedData.map((user) => (
                <tr key={user.id} className="hover">
                  <td className="select-text font-mono text-sm w-[12%]">
                    {user.id}
                  </td>
                  <td className="select-text w-[25%]">{user.name}</td>
                  <td className="select-text w-[25%]">{user.email}</td>
                  <td className="w-[18%]">
                    <select
                      className="select select-bordered select-sm w-full"
                      value={user.rol_id}
                      onChange={(e) =>
                        onToggleRol(user.id, Number(e.target.value))
                      }
                    >
                      {roles.map((rol) => (
                        <option key={rol.id} value={rol.id}>
                          {rol.name}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="w-[20%]">
                    <div className="flex items-center gap-2">
                      <select
                        className="select select-bordered select-sm flex-1"
                        value={user.state ? "activo" : "inactivo"}
                        onChange={() => onToggleState(user.id)}
                      >
                        <option value="activo">Activo</option>
                        <option value="inactivo">Inactivo</option>
                      </select>
                    </div>
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
          Mostrando {paginatedData.length} de {data.length} usuario
          {data.length !== 1 ? "s" : ""}
        </div>
        <div className="join">
          <button
            className="join-item btn btn-sm"
            disabled={page === 1 || data.length === 0}
            onClick={() => setPage(page - 1)}
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
            Página {data.length === 0 ? 0 : page} de {totalPages}
          </button>
          <button
            className="join-item btn btn-sm"
            disabled={page >= totalPages || data.length === 0}
            onClick={() => setPage(page + 1)}
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
