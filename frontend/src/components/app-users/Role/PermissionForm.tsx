import { useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import ConfirmationModal from "./ConfirmationModal";
import type { Permiso } from "../../../types/userApp";
import CustomSelect from "../../Common/Form/CustomSelect";

type Props = {
  permisoList: Permiso[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  onPermissionChange: () => void;
};

export default function PermissionForm({
  permisoList = [],
  setToast,
  onPermissionChange,
}: Props) {
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [selectedPermissionId, setSelectedPermissionId] = useState<string>("");
  const [permissionName, setPermissionName] = useState("");
  const [menuPath, setMenuPath] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [confirmationModal, setConfirmationModal] = useState<{
    isOpen: boolean;
    typeOperation: "eliminar" | "crear" | "actualizar";
    typeChange?: "rol" | "permiso";
    itemIdentifier?: number | string;
    warningMessage?: string;
    onConfirm: () => void;
  }>({
    isOpen: false,
    typeOperation: "crear",
    onConfirm: () => {},
  });

  const handlePermissionSelect = (permissionId: string) => {
    setSelectedPermissionId(permissionId);
    const permission = permisoList.find((p) => p.id === Number(permissionId));
    if (permission) {
      setPermissionName(permission.nombre);
      setMenuPath(permission.menu_path);
    } else {
      setPermissionName("");
      setMenuPath("");
    }
  };

  const showConfirmationModal = (
    typeOperation: "eliminar" | "crear" | "actualizar",
    typeChange: "rol" | "permiso" | undefined,
    itemIdentifier: number | string,
    onConfirm: () => void,
  ) => {
    setConfirmationModal({
      isOpen: true,
      typeOperation,
      typeChange,
      itemIdentifier,
      onConfirm,
    });
  };

  const hideConfirmationModal = () => {
    setConfirmationModal({
      isOpen: false,
      typeOperation: "crear",
      typeChange: undefined,
      itemIdentifier: undefined,
      onConfirm: () => {},
    });
  };

  const executeSubmit = async () => {
    setIsSubmitting(true);
    hideConfirmationModal();

    try {
      const endpoint =
        mode === "create"
          ? API_CONFIG.ENDPOINTS.PERMISSION_ADD
          : API_CONFIG.ENDPOINTS.PERMISSION_UPDATE(selectedPermissionId);

      const res = await apiCall(endpoint, {
        method: mode === "create" ? "POST" : "PUT",
        body: JSON.stringify({
          name: permissionName,
          menu_path: menuPath,
        }),
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: `Permiso ${mode === "create" ? "creado" : "actualizado"} correctamente`,
          type: "success",
        });

        setPermissionName("");
        setMenuPath("");
        setSelectedPermissionId("");

        onPermissionChange();
      } else {
        setToast({
          id: Date.now(),
          message:
            res.detail ||
            `Error al ${mode === "create" ? "crear" : "actualizar"} el permiso`,
          type: "error",
        });
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: `Error al ${mode === "create" ? "crear" : "actualizar"} el permiso`,
        type: "error",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = async () => {
    if (!permissionName.trim()) {
      setToast({
        id: Date.now(),
        message: "El nombre del permiso es obligatorio",
        type: "error",
      });
      return;
    }

    if (mode === "edit" && !selectedPermissionId) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar un permiso para editar",
        type: "error",
      });
      return;
    }

    const actionText = mode === "create" ? "crear" : "actualizar";

    showConfirmationModal(actionText, "permiso", permissionName, executeSubmit);
  };

  const executeDelete = async () => {
    if (!selectedPermissionId) return;

    hideConfirmationModal();

    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.PERMISSION_DELETE(selectedPermissionId),
        {
          method: "DELETE",
        },
      );

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Permiso eliminado correctamente",
          type: "success",
        });

        setPermissionName("");
        setMenuPath("");
        setSelectedPermissionId("");
        onPermissionChange();
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al eliminar el permiso",
          type: "error",
        });
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: "Error al eliminar el permiso",
        type: "error",
      });
    }
  };

  const handleDelete = () => {
    if (!selectedPermissionId || !permissionName) return;

    showConfirmationModal("eliminar", "permiso", permissionName, executeDelete);
  };

  const handleClear = () => {
    setPermissionName("");
    setMenuPath("");
    setSelectedPermissionId("");
  };

  const filteredPermissions = permisoList.filter(
    (p) =>
      p.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
      p.menu_path.toLowerCase().includes(searchTerm.toLowerCase()),
  );

  const generateDynamicCategories = () => {
    const prefixes = new Set<string>();

    permisoList.forEach((perm) => {
      const prefix = perm.nombre.split("_")[0] + "_";
      if (prefix !== "_") prefixes.add(prefix);
    });

    const colorPalette = [
      "badge-primary",
      "badge-success",
      "badge-warning",
      "badge-error",
      "badge-info",
      "badge-secondary",
      "badge-accent",
    ];

    // Mapeo de nombres especiales para consistencia
    const nameMap: { [key: string]: string } = {
      admin_: "Administración",
      sancionatorio_: "Sancionatorio",
      documento_: "Documentos",
      auditoria_: "Auditoría",
      infracciones_: "Infracciones",
      multas_: "Multas",
      usuarios_: "Usuarios",
      reportes_: "Reportes",
    };

    const categoryNames: { [key: string]: { name: string; color: string } } =
      {};
    let index = 0;

    Array.from(prefixes).forEach((prefix) => {
      // Usar nameMap si existe, si no, capitalizar el prefijo de forma limpia
      const rawName = prefix.replace(/_/g, "");
      const name =
        nameMap[prefix] || rawName.charAt(0).toUpperCase() + rawName.slice(1);

      categoryNames[prefix] = {
        name,
        color: colorPalette[index % colorPalette.length],
      };
      index++;
    });

    // Agregar categoría "otros"
    categoryNames["otros"] = { name: "Otros", color: "badge-ghost" };

    return categoryNames;
  };

  const groupPermissionsByCategory = () => {
    const grouped: { [key: string]: Permiso[] } = {};

    const prefixes = new Set<string>();
    permisoList.forEach((perm) => {
      const prefix = perm.nombre.split("_")[0] + "_";
      if (prefix !== "_") prefixes.add(prefix);
    });

    Array.from(prefixes).forEach((prefix) => {
      grouped[prefix] = [];
    });
    grouped["otros"] = [];

    filteredPermissions.forEach((perm) => {
      const prefix = perm.nombre.split("_")[0] + "_";
      if (grouped[prefix]) {
        grouped[prefix].push(perm);
      } else {
        grouped.otros.push(perm);
      }
    });

    return grouped;
  };

  const categoryNames = generateDynamicCategories();
  const groupedPermissions = groupPermissionsByCategory();

  return (
    <>
    <div className="flex-1 min-h-0 flex flex-col lg:flex-row divide-y lg:divide-y-0 lg:divide-x divide-base-300">
      {/* Panel de formulario */}
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
                onClick={() => {
                  setMode("create");
                  handleClear();
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
                    ? "bg-cyan-600 text-white hover:bg-cyan-700 border-0"
                    : "btn-ghost"
                }`}
                onClick={() => {
                  setMode("edit");
                  handleClear();
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

            {/* Selector de permiso (solo en modo editar) */}
            {mode === "edit" && (
              <div className="form-control mb-4">
                <label className="label">
                  <span className="label-text font-semibold">
                    Seleccionar Permiso
                  </span>
                </label>
                <CustomSelect
                  className="focus:border-blue-600"
                  value={selectedPermissionId}
                  onChange={handlePermissionSelect}
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
            <div className="form-control mb-4">
              <label className="label">
                <span className="label-text font-semibold">
                  Nombre del Permiso
                </span>
                <span className="label-text-alt text-error">*</span>
              </label>
              <input
                type="text"
                placeholder="Ej: admin_registrar_usuarios"
                className="input input-bordered w-full focus:border-blue-600"
                value={permissionName}
                onChange={(e) => setPermissionName(e.target.value)}
              />
              <label className="label">
                <span className="label-text-alt text-base-content/60">
                  Use un prefijo seguido de guion bajo, Ej: admin_ver
                </span>
              </label>
            </div>

            {/* Ruta del menú */}
            <div className="form-control mb-4">
              <label className="label">
                <span className="label-text font-semibold">
                  Ruta del Menú (Opcional)
                </span>
              </label>
              <input
                type="text"
                placeholder="Ej: /user/add"
                className="input input-bordered w-full focus:border-blue-600"
                value={menuPath}
                onChange={(e) => setMenuPath(e.target.value)}
              />
              <label className="label">
                <span className="label-text-alt text-base-content/60">
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
                onClick={handleSubmit}
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
                  onClick={handleDelete}
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

              <button className="btn btn-ghost w-full" onClick={handleClear}>
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

      {/* Panel de lista de permisos */}
      <div className="lg:w-2/3 flex-1 min-h-0 flex flex-col">
        <div className="p-6 flex flex-col flex-1 min-h-0">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold flex items-center gap-2">
                <svg
                  className="w-6 h-6 text-blue-600"
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
                Lista de Permisos ({filteredPermissions.length})
              </h3>

              {/* Búsqueda */}
              <div className="form-control">
                <div className="input-group">
                  <input
                    type="text"
                    placeholder="Buscar..."
                    className="input input-bordered input-sm w-64 focus:border-blue-600"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
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
              {Object.entries(groupedPermissions).map(([key, perms]) => {
                if (perms.length === 0) return null;

                return (
                  <div key={key}>
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`badge ${categoryNames[key].color} gap-2`}
                      >
                        {categoryNames[key].name}
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
                            onClick={() => {
                              setMode("edit");
                              handlePermissionSelect(permission.id.toString());
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
    </div>

      {/* Modal de confirmación dinámico */}
      <ConfirmationModal
        isOpen={confirmationModal.isOpen}
        typeOperation={confirmationModal.typeOperation}
        typeChange={confirmationModal.typeChange}
        itemIdentifier={confirmationModal.itemIdentifier}
        isSubmitting={isSubmitting}
        onConfirm={confirmationModal.onConfirm}
        onClose={hideConfirmationModal}
      />
    </>
  );
}
