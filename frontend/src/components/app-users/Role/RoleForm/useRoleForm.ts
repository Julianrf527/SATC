import { useEffect, useState } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import type { Permiso, Rol } from "../../../../types/userApp";
import { generateCategories } from "./permissionCategories";

export type SetToast = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;

type ConfirmationModalState = {
  isOpen: boolean;
  typeOperation: "eliminar" | "crear" | "actualizar";
  typeChange?: "rol" | "permiso";
  itemIdentifier?: number | string;
  onConfirm: () => void;
};

/**
 * Estado y acciones del formulario de roles: carga de roles, selección de
 * permisos, alta/edición/eliminación y modal de confirmación.
 */
export function useRoleForm(permisoList: Permiso[], setToast: SetToast) {
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [rolList, setRolList] = useState<Rol[]>([]);
  const [selectedRoleId, setSelectedRoleId] = useState<string>("");
  const [roleName, setRoleName] = useState("");
  const [selectedPermissions, setSelectedPermissions] = useState<number[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [confirmationModal, setConfirmationModal] =
    useState<ConfirmationModalState>({
      isOpen: false,
      typeOperation: "crear",
      onConfirm: () => {},
    });

  const categories = generateCategories(permisoList);

  const [expandedCategories, setExpandedCategories] = useState<string[]>(
    categories.map((c) => c.prefix),
  );

  const loadRoles = async () => {
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.ROL_PERMISSIONS, {
        method: "GET",
      });
      if (res.ok) {
        setRolList(res.data || []);
      }
    } catch (e) {
      if (import.meta.env.DEV) console.error(e);
    }
  };

  useEffect(() => {
    loadRoles();
  }, []);

  useEffect(() => {
    setExpandedCategories(categories.map((c) => c.prefix));
  }, [permisoList]);

  const handleRoleSelect = (roleId: string) => {
    setSelectedRoleId(roleId);
    const rol = rolList.find((r) => r.id === Number(roleId));
    if (rol) {
      setRoleName(rol.nombre);
      setSelectedPermissions(rol.permisos || []);
    } else {
      setRoleName("");
      setSelectedPermissions([]);
    }
  };

  const toggleCategory = (prefix: string) => {
    setExpandedCategories((prev) =>
      prev.includes(prefix)
        ? prev.filter((p) => p !== prefix)
        : [...prev, prefix],
    );
  };

  const togglePermission = (permissionId: number) => {
    setSelectedPermissions((prev) =>
      prev.includes(permissionId)
        ? prev.filter((id) => id !== permissionId)
        : [...prev, permissionId],
    );
  };

  const toggleCategoryPermissions = (prefix: string) => {
    const categoryPermissions = permisoList
      .filter((p) => p.nombre.startsWith(prefix))
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

  const getFilteredPermissions = (prefix: string) => {
    return permisoList.filter(
      (p) =>
        p.nombre.startsWith(prefix) &&
        (searchTerm === "" ||
          p.nombre.toLowerCase().includes(searchTerm.toLowerCase()) ||
          p.menu_path.toLowerCase().includes(searchTerm.toLowerCase())),
    );
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

  // Asume que el llamador ya validó: se invoca desde el modal de confirmación.
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
          nombre: roleName,
          permisos: selectedPermissions,
        }),
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: `Rol ${mode === "create" ? "creado" : "actualizado"} correctamente`,
          type: "success",
        });

        setRoleName("");
        setSelectedPermissions([]);
        setSelectedRoleId("");

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

  const handleSubmit = async () => {
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

    const actionText = mode === "create" ? "crear" : "actualizar";

    showConfirmationModal(actionText, "rol", roleName, executeSubmit);
  };

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

  const handleDelete = () => {
    if (!selectedRoleId || !roleName) return;

    showConfirmationModal("eliminar", "rol", roleName, executeDelete);
  };

  const handleClear = () => {
    setRoleName("");
    setSelectedPermissions([]);
    setSelectedRoleId("");
    setSearchTerm("");
  };

  return {
    mode,
    setMode,
    rolList,
    selectedRoleId,
    roleName,
    setRoleName,
    selectedPermissions,
    searchTerm,
    setSearchTerm,
    isSubmitting,
    confirmationModal,
    categories,
    expandedCategories,
    handleRoleSelect,
    toggleCategory,
    togglePermission,
    toggleCategoryPermissions,
    getFilteredPermissions,
    hideConfirmationModal,
    handleSubmit,
    handleDelete,
    handleClear,
  };
}
