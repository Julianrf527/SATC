import type { Permiso } from "../../types";
import type { GrupoPermisos } from "./usePermissionForm";

type Props = {
  groups: GrupoPermisos[];
  filteredCount: number;
  searchTerm: string;
  onSearchTermChange: (term: string) => void;
  onEdit: (permission: Permiso) => void;
};

/** Panel derecho: buscador y permisos agrupados por categoría. */
export default function PermissionListPanel({
  groups,
  filteredCount,
  searchTerm,
  onSearchTermChange,
  onEdit,
}: Props) {
  return (
    <div className="lg:w-2/3 flex-1 min-h-0 flex flex-col">
      <div className="p-6 flex flex-col flex-1 min-h-0">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold flex items-center gap-2">
              <svg
                className="w-6 h-6 text-info"
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
              Lista de Permisos ({filteredCount})
            </h3>

            {/* Búsqueda */}
            <div className="flex flex-col">
              <div className="join">
                <input
                  type="text"
                  placeholder="Buscar..."
                  className="input input-sm w-64 focus:border-info"
                  value={searchTerm}
                  onChange={(e) => onSearchTermChange(e.target.value)}
                />
                <button className="btn btn-square btn-sm btn-ghost">
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
                      d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          <div className="divider my-2"></div>

          {/* Lista de permisos agrupados */}
          <div className="space-y-4 overflow-y-auto flex-1 min-h-0">
            {groups.map(({ key, name, color, permisos: perms }) => {
                  return (
                <div key={key}>
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className={`badge ${color} gap-2`}
                    >
                      {name}
                    </span>
                    <span className="text-sm text-base-content/60">
                      {perms.length} permisos
                    </span>
                  </div>
                  <div className="grid grid-cols-1 gap-2">
                    {perms.map((permission) => (
                      <div
                        key={permission.id}
                        className="flex items-center justify-between p-3 bg-base-200 rounded-lg hover:bg-base-300 transition-colors"
                      >
                        <div className="flex-1">
                          <div className="font-medium text-sm">
                            {permission.nombre}
                          </div>
                          <div className="text-xs text-base-content/60">
                            {permission.menu_path || "Sin ruta de menú"}
                          </div>
                        </div>
                        <button
                          className="btn btn-sm btn-ghost btn-square"
                          onClick={() => onEdit(permission)}
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
                              d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                            />
                          </svg>
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
      </div>
    </div>
  );
}
