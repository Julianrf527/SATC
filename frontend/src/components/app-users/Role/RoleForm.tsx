import { useState, useEffect } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import ConfirmationModal from "./ConfirmationModal";

type Permission = {
  id: number;
  name: string;
  menu_path: string;
};

type Role = {
  id: number;
  name: string;
  permission: number[];
};

type Props = {
  permissions: Permission[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

type PermissionCategory = {
  name: string;
  prefix: string;
  color: string;
  icon: string;
};

// Mapeo de iconos conocidos (para categorías existentes y futuras)
const iconMap: { [key: string]: string } = {
  admin_:
    "M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z",
  expediente_:
    "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  documento_:
    "M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z",
  auditoria_:
    "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01",
  infracciones_:
    "M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.992-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z",
  multas_:
    "M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z",
  usuarios_:
    "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z",
  reportes_:
    "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  // Icono genérico para categorías nuevas
  default:
    "M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
};

// Colores para las categorías (se rotan si hay más categorías)
const colorPalette = [
  "badge-primary",
  "badge-success",
  "badge-warning",
  "badge-error",
  "badge-info",
  "badge-secondary",
  "badge-accent",
];

// Función para generar categorías dinámicamente
const generateCategories = (
  permissions: Permission[],
): PermissionCategory[] => {
  const prefixes = new Set<string>();

  // Extraer todos los prefijos únicos
  permissions.forEach((perm) => {
    const prefix = perm.name.split("_")[0] + "_";
    if (prefix !== "_") prefixes.add(prefix);
  });

  // Mapeo de nombres especiales
  const nameMap: { [key: string]: string } = {
    admin_: "Administración",
    expediente_: "Expedientes",
    documento_: "Documentos",
    auditoria_: "Auditoría",
    infracciones_: "Infracciones",
    multas_: "Multas",
    usuarios_: "Usuarios",
    reportes_: "Reportes",
  };

  // Convertir prefijos a categorías
  return Array.from(prefixes).map((prefix, index) => {
    // Usar nameMap si existe, si no, capitalizar el prefijo de forma limpia
    const rawName = prefix.replace(/_/g, "");
    const name =
      nameMap[prefix] ||
      rawName.charAt(0).toUpperCase() + rawName.slice(1);

    return {
      name,
      prefix,
      color: colorPalette[index % colorPalette.length],
      icon: iconMap[prefix] || iconMap.default,
    };
  });
};

export default function RoleForm({ permissions, setToast }: Props) {
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string>("");
  const [roleName, setRoleName] = useState("");
  const [selectedPermissions, setSelectedPermissions] = useState<number[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmationModal, setConfirmationModal] = useState<{
    isOpen: boolean;
    typeOperation: "eliminar" | "crear" | "actualizar";
    typeChange?: "rol" | "permiso";
    itemIdentifier?: number | string;
    onConfirm: () => void;
  }>({
    isOpen: false,
    typeOperation: "crear",
    onConfirm: () => {},
  });

  // Generar categorías dinámicamente basándose en los permisos recibidos
  const categories = generateCategories(permissions);

  const [expandedCategories, setExpandedCategories] = useState<string[]>(
    categories.map((c) => c.prefix),
  );

  // Cargar roles
  const loadRoles = async () => {
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.ROL_PERMISSIONS, {
        method: "GET",
      });
      if (res.ok) {
        setRoles(res.data || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadRoles();
  }, []);

  // Actualizar categorías expandidas cuando cambien los permisos
  useEffect(() => {
    setExpandedCategories(categories.map((c) => c.prefix));
  }, [permissions]);

  // Manejar selección de rol para editar
  const handleRoleSelect = (roleId: string) => {
    setSelectedRoleId(roleId);
    const role = roles.find((r) => r.id === Number(roleId));
    if (role) {
      setRoleName(role.name);
      setSelectedPermissions(role.permission || []); // Fix: asegurar que siempre sea array
    } else {
      setRoleName("");
      setSelectedPermissions([]);
    }
  };

  // Toggle categoría expandida/colapsada
  const toggleCategory = (prefix: string) => {
    setExpandedCategories((prev) =>
      prev.includes(prefix)
        ? prev.filter((p) => p !== prefix)
        : [...prev, prefix],
    );
  };

  // Toggle permiso individual
  const togglePermission = (permissionId: number) => {
    setSelectedPermissions((prev) =>
      prev.includes(permissionId)
        ? prev.filter((id) => id !== permissionId)
        : [...prev, permissionId],
    );
  };

  // Toggle todos los permisos de una categoría
  const toggleCategoryPermissions = (prefix: string) => {
    const categoryPermissions = permissions
      .filter((p) => p.name.startsWith(prefix))
      .map((p) => p.id);

    const allSelected = categoryPermissions.every((id) =>
      selectedPermissions.includes(id),
    );

    if (allSelected) {
      setSelectedPermissions((prev) =>
        prev.filter((id) => !categoryPermissions.includes(id)),
      );
    } else {
      setSelectedPermissions((prev) => [
        ...new Set([...prev, ...categoryPermissions]),
      ]);
    }
  };

  // Filtrar permisos por búsqueda
  const getFilteredPermissions = (prefix: string) => {
    return permissions.filter(
      (p) =>
        p.name.startsWith(prefix) &&
        (searchTerm === "" ||
          p.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          p.menu_path.toLowerCase().includes(searchTerm.toLowerCase())),
    );
  };

  // Formatear nombre de permiso
  const formatPermissionName = (name: string, prefix: string) => {
    return name
      .replace(prefix, "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  // Funciones auxiliares del modal de confirmación
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

  // Función interna para ejecutar crear/actualizar (sin validaciones duplicadas)
  const executeSubmit = async () => {
    setIsSubmitting(true);
    hideConfirmationModal();

    try {
      const endpoint =
        mode === "create"
          ? API_CONFIG.ENDPOINTS.ROL_ADD
          : API_CONFIG.ENDPOINTS.ROL_UPDATE(selectedRoleId);

      const res = await apiCall(endpoint, {
        method: mode === "create" ? "POST" : "PUT",
        body: JSON.stringify({
          name: roleName,
          permission: selectedPermissions,
        }),
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: `Rol ${mode === "create" ? "creado" : "actualizado"} correctamente`,
          type: "success",
        });

        // Resetear formulario
        setRoleName("");
        setSelectedPermissions([]);
        setSelectedRoleId("");

        // Recargar roles
        await loadRoles();
      } else {
        setToast({
          id: Date.now(),
          message:
            res.detail ||
            `Error al ${mode === "create" ? "crear" : "actualizar"} el rol`,
          type: "error",
        });
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: `Error al ${mode === "create" ? "crear" : "actualizar"} el rol`,
        type: "error",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Crear o actualizar rol (con modal de confirmación)
  const handleSubmit = async () => {
    // Validaciones
    if (!roleName.trim()) {
      setToast({
        id: Date.now(),
        message: "El nombre del rol es obligatorio",
        type: "error",
      });
      return;
    }

    if (selectedPermissions.length === 0) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar al menos un permiso",
        type: "error",
      });
      return;
    }

    if (mode === "edit" && !selectedRoleId) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar un rol para editar",
        type: "error",
      });
      return;
    }

    // Mostrar modal de confirmación
    const actionText = mode === "create" ? "crear" : "actualizar";

    showConfirmationModal(
      actionText,
      "rol",
      roleName,
      executeSubmit
    );
  };

  // Función interna para ejecutar eliminación
  const executeDelete = async () => {
    if (!selectedRoleId) return;

    hideConfirmationModal();

    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.ROL_DELETE(selectedRoleId),
        {
          method: "DELETE",
        },
      );

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Rol eliminado correctamente",
          type: "success",
        });

        setRoleName("");
        setSelectedPermissions([]);
        setSelectedRoleId("");
        await loadRoles();
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al eliminar el rol",
          type: "error",
        });
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: "Error al eliminar el rol",
        type: "error",
      });
    }
  };

  // Eliminar rol (con modal de confirmación)
  const handleDelete = () => {
    if (!selectedRoleId || !roleName) return;

    showConfirmationModal(
      "eliminar",
      "rol",
      roleName,
      executeDelete
    );
  };

  // Limpiar formulario
  const handleClear = () => {
    setRoleName("");
    setSelectedPermissions([]);
    setSelectedRoleId("");
    setSearchTerm("");
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      {/* Panel de configuración */}
      <div className="xl:col-span-1">
        <div className="card bg-base-100 shadow-xl border border-base-300 sticky top-4">
          <div className="card-body">
            {/* Selector de modo */}
            <div className="flex gap-2 mb-4">
              <button
                className={`btn btn-sm flex-1 ${
                  mode === "create"
                    ? "bg-green-600 text-white hover:bg-green-700 border-0"
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
                    ? "bg-green-600 text-white hover:bg-green-700 border-0"
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

            {/* Selector de rol (solo en modo editar) */}
            {mode === "edit" && (
              <div className="form-control mb-4">
                <label className="label">
                  <span className="label-text font-semibold">
                    Seleccionar Rol
                  </span>
                </label>
                <select
                  className="select select-bordered w-full focus:border-green-600"
                  value={selectedRoleId}
                  onChange={(e) => handleRoleSelect(e.target.value)}
                >
                  <option value="">-- Seleccione un rol --</option>
                  {roles.map((role) => (
                    <option key={role.id} value={role.id}>
                      {role.name} ({role.permission?.length || 0} permisos)
                    </option>
                  ))}
                </select>
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
                onChange={(e) => setRoleName(e.target.value)}
              />
            </div>

            {/* Estadísticas */}
            <div className="stats stats-vertical shadow-sm mb-4">
              <div className="stat py-3">
                <div className="stat-title text-xs">Permisos Seleccionados</div>
                <div className="stat-value text-2xl text-green-600">
                  {selectedPermissions.length}
                </div>
                <div className="stat-desc">de {permissions.length} totales</div>
              </div>
            </div>

            {/* Botones de acción */}
            <div className="flex flex-col gap-2">
              <button
                className={`btn ${
                  mode === "create"
                    ? "bg-green-600 text-white hover:bg-green-700 border-0"
                    : "bg-green-600 text-white hover:bg-green-700 border-0"
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
                    {mode === "create" ? "Crear Rol" : "Guardar Cambios"}
                  </>
                )}
              </button>

              {mode === "edit" && selectedRoleId && (
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
                  Eliminar Rol
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
      </div>

      {/* Panel de permisos */}
      <div className="xl:col-span-2">
        <div className="card bg-base-100 shadow-xl border border-base-300">
          <div className="card-body">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold flex items-center gap-2">
                <svg
                  className="w-6 h-6 text-green-600"
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
              <div className="form-control">
                <div className="input-group">
                  <input
                    type="text"
                    placeholder="Buscar permisos..."
                    className="input input-bordered input-sm w-64 focus:border-green-600"
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

            {/* Categorías de permisos */}
            <div className="space-y-4 max-h-[600px] overflow-y-auto">
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
                      onChange={() => toggleCategory(category.prefix)}
                    />
                    <div className="collapse-title flex items-center justify-between pr-12">
                      <div className="flex items-center gap-3">
                        <div
                          className={`badge ${category.color} badge-lg`}
                        >
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
                            toggleCategoryPermissions(category.prefix);
                          }}
                          onClick={(e) => e.stopPropagation()}
                        />
                        <span className="text-xs text-base-content/60">
                          Todos
                        </span>
                      </div>
                    </div>
                    <div className="collapse-content">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
                        {categoryPerms.map((permission) => (
                          <label
                            key={permission.id}
                            className="flex items-center gap-3 p-3 bg-base-100 rounded-lg hover:bg-base-300 cursor-pointer transition-colors border border-base-300"
                          >
                            <input
                              type="checkbox"
                              className="checkbox checkbox-success checkbox-sm"
                              checked={selectedPermissions.includes(
                                permission.id,
                              )}
                              onChange={() => togglePermission(permission.id)}
                            />
                            <div className="flex-1">
                              <div className="font-medium text-sm">
                                {formatPermissionName(
                                  permission.name,
                                  category.prefix,
                                )}
                              </div>
                              {permission.menu_path && (
                                <div className="text-xs text-base-content/50">
                                  {permission.menu_path}
                                </div>
                              )}
                            </div>
                          </label>
                        ))}
                      </div>
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
        onClose={hideConfirmationModal}
        onConfirm={confirmationModal.onConfirm}
        typeOperation={confirmationModal.typeOperation}
        typeChange={confirmationModal.typeChange}
        itemIdentifier={confirmationModal.itemIdentifier}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}
