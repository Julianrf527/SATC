import type { Rol } from "../../../../types/userApp";
import CustomSelect from "../../../Common/Form/CustomSelect";

type Props = {
  mode: "create" | "edit";
  onModeChange: (mode: "create" | "edit") => void;
  rolList: Rol[];
  selectedRoleId: string;
  onRoleSelect: (roleId: string) => void;
  roleName: string;
  onRoleNameChange: (name: string) => void;
  selectedCount: number;
  totalPermissions: number;
  isSubmitting: boolean;
  onSubmit: () => void;
  onDelete: () => void;
  onClear: () => void;
};

export default function RoleConfigPanel({
  mode,
  onModeChange,
  rolList,
  selectedRoleId,
  onRoleSelect,
  roleName,
  onRoleNameChange,
  selectedCount,
  totalPermissions,
  isSubmitting,
  onSubmit,
  onDelete,
  onClear,
}: Props) {
  return (
    <div className="xl:w-1/3 flex-none overflow-y-auto h-full">
      <div className="p-6 h-full flex flex-col">
          {/* Selector de modo */}
          <div className="flex gap-2 mb-4">
            <button
              className={`btn btn-sm flex-1 ${
                mode === "create"
                  ? "bg-green-600 text-white hover:bg-green-700 border-0"
                  : "btn-ghost"
              }`}
              onClick={() => {
                onModeChange("create");
                onClear();
              }}
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
                  d="M12 4v16m8-8H4"
                />
              </svg>
              Crear
            </button>
            <button
              className={`btn btn-sm flex-1 ${
                mode === "edit"
                  ? "bg-green-600 text-white hover:bg-green-700 border-0"
                  : "btn-ghost"
              }`}
              onClick={() => {
                onModeChange("edit");
                onClear();
              }}
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
              Editar
            </button>
          </div>

          <div className="divider my-2"></div>

          {/* Selector de rol (solo en modo editar) */}
          {mode === "edit" && (
            <div className="form-control mb-4">
              <label className="label">
                <span className="label-text font-semibold">
                  Seleccionar Rol
                </span>
              </label>
              <CustomSelect
                className="focus:border-green-600"
                value={selectedRoleId}
                onChange={onRoleSelect}
                emptyValue=""
                placeholder="-- Seleccione un rol --"
                options={rolList.map((rol) => ({
                  value: String(rol.id),
                  label: `${rol.nombre} (${rol.permisos?.length || 0} permisos)`,
                }))}
              />
            </div>
          )}

          {/* Nombre del rol */}
          <div className="form-control mb-4">
            <label className="label">
              <span className="label-text font-semibold">Nombre del Rol</span>
              <span className="label-text-alt text-error">*</span>
            </label>
            <input
              type="text"
              placeholder="Ej: Editor, Supervisor..."
              className="input input-bordered w-full focus:border-green-600"
              value={roleName}
              onChange={(e) => onRoleNameChange(e.target.value)}
            />
          </div>

          {/* Estadísticas */}
          <div className="stats stats-vertical shadow-sm mb-4">
            <div className="stat py-3">
              <div className="stat-title text-xs">Permisos Seleccionados</div>
              <div className="stat-value text-2xl text-green-600">
                {selectedCount}
              </div>
              <div className="stat-desc">de {totalPermissions} totales</div>
            </div>
          </div>

          {/* Botones de acción: siempre al fondo del panel */}
          <div className="flex flex-col gap-2 mt-auto pt-4">
            <button
              className={`btn ${
                mode === "create"
                  ? "bg-green-600 text-white hover:bg-green-700 border-0"
                  : "bg-green-600 text-white hover:bg-green-700 border-0"
              } w-full`}
              onClick={onSubmit}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <span className="loading loading-spinner"></span>
              ) : (
                <>
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  {mode === "create" ? "Crear Rol" : "Guardar Cambios"}
                </>
              )}
            </button>

            {mode === "edit" && selectedRoleId && (
              <button
                className="btn btn-error btn-outline w-full"
                onClick={onDelete}
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
                Eliminar Rol
              </button>
            )}

            <button className="btn btn-ghost w-full" onClick={onClear}>
              <svg
                className="w-5 h-5"
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
      </div>
    </div>
  );
}
