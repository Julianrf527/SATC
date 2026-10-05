import CustomSelect from "@shared/ui/form/CustomSelect";
import type { Permiso } from "../../types";

type Props = {
  mode: "create" | "edit";
  onModeChange: (mode: "create" | "edit") => void;
  permisoList: Permiso[];
  selectedPermissionId: string;
  onPermissionSelect: (permissionId: string) => void;
  permissionName: string;
  onPermissionNameChange: (name: string) => void;
  menuPath: string;
  onMenuPathChange: (path: string) => void;
  isSubmitting: boolean;
  onSubmit: () => void;
  onDelete: () => void;
  onClear: () => void;
};

/** Panel izquierdo: modo crear/editar, campos del permiso y acciones. */
export default function PermissionEditorPanel({
  mode,
  onModeChange,
  permisoList,
  selectedPermissionId,
  onPermissionSelect,
  permissionName,
  onPermissionNameChange,
  menuPath,
  onMenuPathChange,
  isSubmitting,
  onSubmit,
  onDelete,
  onClear,
}: Props) {
  return (
    <div className="lg:w-1/3 flex-none overflow-y-auto h-full">
      <div className="p-6 h-full flex flex-col">
          {/* Selector de modo */}
          <div className="flex gap-2 mb-4">
            <button
              className={`btn btn-sm flex-1 ${
                mode === "create"
                  ? "bg-blue-600 text-white hover:bg-blue-700 border-0"
                  : "btn-ghost"
              }`}
              onClick={() => onModeChange("create")}
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
                  ? "bg-cyan-600 text-white hover:bg-cyan-700 border-0"
                  : "btn-ghost"
              }`}
              onClick={() => onModeChange("edit")}
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

          {/* Selector de permiso (solo en modo editar) */}
          {mode === "edit" && (
            <div className="flex flex-col mb-4">
              <label className="label">
                <span className="text-sm text-base-content font-semibold">
                  Seleccionar Permiso
                </span>
              </label>
              <CustomSelect
                className="focus:border-info"
                value={selectedPermissionId}
                onChange={onPermissionSelect}
                emptyValue=""
                placeholder="-- Seleccione un permiso --"
                options={permisoList.map((permission) => ({
                  value: String(permission.id),
                  label: permission.nombre,
                }))}
              />
            </div>
          )}

          {/* Nombre del permiso */}
          <div className="flex flex-col mb-4">
            <label className="label">
              <span className="text-sm text-base-content font-semibold">
                Nombre del Permiso
              </span>
              <span className="text-xs text-error">*</span>
            </label>
            <input
              type="text"
              placeholder="Ej: admin_registrar_usuarios"
              className="input w-full focus:border-info"
              value={permissionName}
              onChange={(e) => onPermissionNameChange(e.target.value)}
            />
            <label className="label">
              <span className="text-xs text-base-content/60">
                Use un prefijo seguido de guion bajo, Ej: admin_ver
              </span>
            </label>
          </div>

          {/* Ruta del menú */}
          <div className="flex flex-col mb-4">
            <label className="label">
              <span className="text-sm text-base-content font-semibold">
                Ruta del Menú (Opcional)
              </span>
            </label>
            <input
              type="text"
              placeholder="Ej: /user/add"
              className="input w-full focus:border-info"
              value={menuPath}
              onChange={(e) => onMenuPathChange(e.target.value)}
            />
            <label className="label">
              <span className="text-xs text-base-content/60">
                Dejar vacío si el permiso no tiene ruta propia
              </span>
            </label>
          </div>

          <div className="divider my-2"></div>

          {/* Botones de acción: siempre al fondo del panel */}
          <div className="flex flex-col gap-2 mt-auto pt-4">
            <button
              className={`btn ${
                mode === "create"
                  ? "bg-blue-600 text-white hover:bg-blue-700 border-0"
                  : "bg-cyan-600 text-white hover:bg-cyan-700 border-0"
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
                  {mode === "create" ? "Crear Permiso" : "Guardar Cambios"}
                </>
              )}
            </button>

            {mode === "edit" && selectedPermissionId && (
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
                Eliminar Permiso
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
