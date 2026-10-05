import { useMemo, useState } from "react";
import type { Permiso, SetToast } from "../../types";
import {
  useDeleteRolMutation,
  useRolesConPermisosQuery,
  useSaveRolMutation,
} from "../../api/roles";
import { apiErrorMessage } from "../../api/errors";
import { useConfirmacion } from "../useConfirmacion";
import { generateCategories } from "./permissionCategories";

/**
 * Estado y acciones del formulario de roles: selección de permisos,
 * alta/edición/eliminación y modal de confirmación. Los datos (roles) vienen
 * de react-query; las mutaciones invalidan `usersKeys.roles()`.
 */
export function useRoleForm(permisoList: Permiso[], setToast: SetToast) {
  const [mode, setMode] = useState<"create" | "edit">("create");
  const [selectedRoleId, setSelectedRoleId] = useState<string>("");
  const [roleName, setRoleName] = useState("");
  const [selectedPermissions, setSelectedPermissions] = useState<number[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const { confirmacion, pedirConfirmacion, cerrarConfirmacion } = useConfirmacion();

  const { data: rolList = [] } = useRolesConPermisosQuery();
  const saveRol = useSaveRolMutation();
  const deleteRol = useDeleteRolMutation();
  const isSubmitting = saveRol.isPending || deleteRol.isPending;

  const categories = useMemo(() => generateCategories(permisoList), [permisoList]);

  // Todas las categorías expandidas al cargar/recargar el catálogo de permisos
  // (ajuste de estado durante el render, sin efecto).
  const [expandedCategories, setExpandedCategories] = useState<string[]>(() =>
    categories.map((c) => c.prefix),
  );
  const [prevPermisoList, setPrevPermisoList] = useState(permisoList);
  if (prevPermisoList !== permisoList) {
    setPrevPermisoList(permisoList);
    setExpandedCategories(categories.map((c) => c.prefix));
  }

  const resetForm = () => {
    setRoleName("");
    setSelectedPermissions([]);
    setSelectedRoleId("");
  };

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
      prev.includes(prefix) ? prev.filter((p) => p !== prefix) : [...prev, prefix],
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

    const allSelected = categoryPermissions.every((id) => selectedPermissions.includes(id));

    if (allSelected) {
      setSelectedPermissions((prev) => prev.filter((id) => !categoryPermissions.includes(id)));
    } else {
      setSelectedPermissions((prev) => [...new Set([...prev, ...categoryPermissions])]);
    }
  };

  const getFilteredPermissions = (prefix: string) => {
    const term = searchTerm.toLowerCase();
    return permisoList.filter(
      (p) =>
        p.nombre.startsWith(prefix) &&
        (searchTerm === "" ||
          p.nombre.toLowerCase().includes(term) ||
          p.menu_path.toLowerCase().includes(term)),
    );
  };

  // Asume que el llamador ya validó: se invoca desde el modal de confirmación.
  const executeSubmit = () => {
    cerrarConfirmacion();
    const accion = mode === "create" ? "crear" : "actualizar";
    saveRol.mutate(
      {
        id: mode === "create" ? undefined : selectedRoleId,
        nombre: roleName,
        permisos: selectedPermissions,
      },
      {
        onSuccess: () => {
          setToast({
            id: Date.now(),
            message: `Rol ${mode === "create" ? "creado" : "actualizado"} correctamente`,
            type: "success",
          });
          resetForm();
        },
        onError: (e) =>
          setToast({
            id: Date.now(),
            message: apiErrorMessage(e, `Error al ${accion} el rol`),
            type: "error",
          }),
      },
    );
  };

  const handleSubmit = () => {
    if (!roleName.trim()) {
      setToast({ id: Date.now(), message: "El nombre del rol es obligatorio", type: "error" });
      return;
    }

    if (selectedPermissions.length === 0) {
      setToast({ id: Date.now(), message: "Debe seleccionar al menos un permiso", type: "error" });
      return;
    }

    if (mode === "edit" && !selectedRoleId) {
      setToast({ id: Date.now(), message: "Debe seleccionar un rol para editar", type: "error" });
      return;
    }

    const actionText = mode === "create" ? "crear" : "actualizar";
    pedirConfirmacion(actionText, "rol", roleName, executeSubmit);
  };

  const executeDelete = () => {
    if (!selectedRoleId) return;
    cerrarConfirmacion();
    deleteRol.mutate(selectedRoleId, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Rol eliminado correctamente", type: "success" });
        resetForm();
      },
      onError: (e) =>
        setToast({
          id: Date.now(),
          message: apiErrorMessage(e, "Error al eliminar el rol"),
          type: "error",
        }),
    });
  };

  const handleDelete = () => {
    if (!selectedRoleId || !roleName) return;
    pedirConfirmacion("eliminar", "rol", roleName, executeDelete);
  };

  const handleClear = () => {
    resetForm();
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
    confirmationModal: confirmacion,
    categories,
    expandedCategories,
    handleRoleSelect,
    toggleCategory,
    togglePermission,
    toggleCategoryPermissions,
    getFilteredPermissions,
    hideConfirmationModal: cerrarConfirmacion,
    handleSubmit,
    handleDelete,
    handleClear,
  };
}
