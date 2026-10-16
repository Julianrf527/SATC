import type { Permiso } from "../../types";
import {
  formatPermissionName,
  type PermissionCategory,
} from "./permissionCategories";
import type { EstadoPermiso } from "./useRoleForm";

type Props = {
  categories: PermissionCategory[];
  searchTerm: string;
  onSearchTermChange: (term: string) => void;
  expandedCategories: string[];
  selectedPermissions: number[];
  getFilteredPermissions: (prefix: string) => Permiso[];
  onToggleCategory: (prefix: string) => void;
  onToggleCategoryPermissions: (prefix: string) => void;
  onTogglePermission: (permissionId: number) => void;
  getEstadoPermiso: (permission: Permiso) => EstadoPermiso;
  avisoCascada: string | null;
  onCerrarAvisoCascada: () => void;
};

export default function PermissionSelector({
  categories,
  searchTerm,
  onSearchTermChange,
  expandedCategories,
  selectedPermissions,
  getFilteredPermissions,
  onToggleCategory,
  onToggleCategoryPermissions,
  onTogglePermission,
  getEstadoPermiso,
  avisoCascada,
  onCerrarAvisoCascada,
}: Props) {
  return (
    <div className="xl:w-2/3 flex-1 min-h-0 flex flex-col">
      <div className="p-6 flex flex-col flex-1 min-h-0">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold flex items-center gap-2">
              <svg
                className="w-6 h-6 text-success"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
              Seleccionar Permisos
            </h3>

            {/* Búsqueda */}
            <div className="flex flex-col">
              <div className="join">
                <input
                  type="text"
                  placeholder="Buscar permisos..."
                  className="input input-sm w-64 focus:border-success"
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

          {avisoCascada && (
            <div role="status" className="alert alert-info alert-soft py-2 mb-3 text-sm">
              <span className="flex-1">{avisoCascada}</span>
              <button
                type="button"
                className="btn btn-ghost btn-xs"
                aria-label="Cerrar aviso"
                onClick={onCerrarAvisoCascada}
              >
                ✕
              </button>
            </div>
          )}

          {/* Categorías de permisos */}
          <div className="space-y-4 overflow-y-auto flex-1 min-h-0">
            {categories.map((category) => {
              const categoryPerms = getFilteredPermissions(category.prefix);
              const selectedInCategory = categoryPerms.filter((p) =>
                selectedPermissions.includes(p.id),
              ).length;
              const allSelected = selectedInCategory === categoryPerms.length;
              const someSelected = selectedInCategory > 0 && !allSelected;

              if (categoryPerms.length === 0 && searchTerm) return null;

              return (
                <div
                  key={category.prefix}
                  className="collapse collapse-arrow bg-base-200 rounded-box"
                >
                  <input
                    type="checkbox"
                    checked={expandedCategories.includes(category.prefix)}
                    onChange={() => onToggleCategory(category.prefix)}
                  />
                  <div className="collapse-title flex items-center justify-between pr-12">
                    <div className="flex items-center gap-3">
                      <div className={`badge ${category.color} badge-lg`}>
                        {category.name}
                      </div>
                      <div className="text-sm text-base-content/60">
                        {selectedInCategory} / {categoryPerms.length}{" "}
                        seleccionados
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        className={`checkbox checkbox-sm ${
                          allSelected
                            ? "checkbox-success"
                            : someSelected
                              ? "checkbox-success opacity-50"
                              : ""
                        }`}
                        checked={allSelected}
                        onChange={(e) => {
                          e.stopPropagation();
                          onToggleCategoryPermissions(category.prefix);
                        }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <span className="text-xs text-base-content/60">Todos</span>
                    </div>
                  </div>
                  <div className="collapse-content">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                      {categoryPerms.map((permission) => {
                        const { bloqueado, faltan } = getEstadoPermiso(permission);
                        const marcado = selectedPermissions.includes(permission.id);
                        return (
                          <label
                            key={permission.id}
                            title={permission.menu_path || undefined}
                            className={`flex items-start gap-3 p-3 bg-base-100 rounded-lg transition-colors border border-base-300 ${
                              bloqueado
                                ? "opacity-60 cursor-not-allowed"
                                : "hover:bg-base-300 cursor-pointer"
                            }`}
                          >
                            <input
                              type="checkbox"
                              className="checkbox checkbox-success checkbox-sm mt-0.5"
                              checked={marcado}
                              disabled={bloqueado}
                              onChange={() => onTogglePermission(permission.id)}
                            />
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-sm">
                                {formatPermissionName(
                                  permission.nombre,
                                  category.prefix,
                                )}
                              </div>
                              {permission.descripcion ? (
                                <div className="text-xs text-base-content/60 leading-snug">
                                  {permission.descripcion}
                                </div>
                              ) : (
                                permission.menu_path && (
                                  <div className="text-xs text-base-content/60">
                                    {permission.menu_path}
                                  </div>
                                )
                              )}
                              {faltan.length > 0 && (
                                <div
                                  className={`text-xs mt-1 ${marcado ? "text-error" : "text-warning"}`}
                                >
                                  Requiere: {faltan.join(", ")}
                                </div>
                              )}
                            </div>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
      </div>
    </div>
  );
}
