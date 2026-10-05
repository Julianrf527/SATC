import { useMemo, useState } from "react";
import type { Permiso, SetToast } from "../../types";
import {
  useDeletePermissionMutation,
  useSavePermissionMutation,
} from "../../api/permissions";
import { apiErrorMessage } from "../../api/errors";
import { useConfirmacion } from "../useConfirmacion";
import { generateCategories } from "../role-form/permissionCategories";

export type GrupoPermisos = {
  key: string;
  name: string;
  color: string;
  permisos: Permiso[];
};

/**
 * Estado y acciones del formulario de permisos (crear / editar / eliminar).
 * Las mutaciones invalidan el catálogo de permisos, así que la lista se
 * refresca sola.
 */
export function usePermissionForm(permisoList: Permiso[], setToast: SetToast) {
  const [mode, setModeState] = useState<"create" | "edit">("create");
  const [selectedPermissionId, setSelectedPermissionId] = useState<string>("");
  const [permissionName, setPermissionName] = useState("");
  const [menuPath, setMenuPath] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const { confirmacion, pedirConfirmacion, cerrarConfirmacion } = useConfirmacion();

  const savePermission = useSavePermissionMutation();
  const deletePermission = useDeletePermissionMutation();
  const isSubmitting = savePermission.isPending;

  const handleClear = () => {
    setPermissionName("");
    setMenuPath("");
    setSelectedPermissionId("");
  };

  /** Cambiar de modo limpia el formulario (como los botones Crear/Editar). */
  const changeMode = (next: "create" | "edit") => {
    setModeState(next);
    handleClear();
  };

  const handlePermissionSelect = (permissionId: string) => {
    setSelectedPermissionId(permissionId);
    const permission = permisoList.find((p) => p.id === Number(permissionId));
    setPermissionName(permission?.nombre ?? "");
    setMenuPath(permission?.menu_path ?? "");
  };

  /** Botón de editar de la lista: pasa a modo edición con ese permiso cargado. */
  const editPermission = (permission: Permiso) => {
    setModeState("edit");
    handlePermissionSelect(permission.id.toString());
  };

  const executeSubmit = () => {
    cerrarConfirmacion();
    const accion = mode === "create" ? "crear" : "actualizar";
    savePermission.mutate(
      {
        id: mode === "create" ? undefined : selectedPermissionId,
        name: permissionName,
        menu_path: menuPath,
      },
      {
        onSuccess: () => {
          setToast({
            id: Date.now(),
            message: `Permiso ${mode === "create" ? "creado" : "actualizado"} correctamente`,
            type: "success",
          });
          handleClear();
        },
        onError: (e) =>
          setToast({
            id: Date.now(),
            message: apiErrorMessage(e, `Error al ${accion} el permiso`),
            type: "error",
          }),
      },
    );
  };

  const handleSubmit = () => {
    if (!permissionName.trim()) {
      setToast({ id: Date.now(), message: "El nombre del permiso es obligatorio", type: "error" });
      return;
    }

    if (mode === "edit" && !selectedPermissionId) {
      setToast({ id: Date.now(), message: "Debe seleccionar un permiso para editar", type: "error" });
      return;
    }

    const actionText = mode === "create" ? "crear" : "actualizar";
    pedirConfirmacion(actionText, "permiso", permissionName, executeSubmit);
  };

  const executeDelete = () => {
    if (!selectedPermissionId) return;
    cerrarConfirmacion();
    deletePermission.mutate(selectedPermissionId, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Permiso eliminado correctamente", type: "success" });
        handleClear();
      },
      onError: (e) =>
        setToast({
          id: Date.now(),
          message: apiErrorMessage(e, "Error al eliminar el permiso"),
          type: "error",
        }),
    });
  };

  const handleDelete = () => {
    if (!selectedPermissionId || !permissionName) return;
    pedirConfirmacion("eliminar", "permiso", permissionName, executeDelete);
  };

  const filteredPermissions = useMemo(() => {
    const term = searchTerm.toLowerCase();
    return permisoList.filter(
      (p) => p.nombre.toLowerCase().includes(term) || p.menu_path.toLowerCase().includes(term),
    );
  }, [permisoList, searchTerm]);

  // Grupos por prefijo (mismas categorías dinámicas que el editor de roles) + "Otros".
  const groups = useMemo<GrupoPermisos[]>(() => {
    const grupos: GrupoPermisos[] = generateCategories(permisoList).map((c) => ({
      key: c.prefix,
      name: c.name,
      color: c.color,
      permisos: [],
    }));
    const otros: GrupoPermisos = { key: "otros", name: "Otros", color: "badge-ghost", permisos: [] };
    const porPrefijo = new Map(grupos.map((g) => [g.key, g]));

    filteredPermissions.forEach((perm) => {
      const prefix = perm.nombre.split("_")[0] + "_";
      (porPrefijo.get(prefix) ?? otros).permisos.push(perm);
    });

    return [...grupos, otros].filter((g) => g.permisos.length > 0);
  }, [permisoList, filteredPermissions]);

  return {
    mode,
    changeMode,
    selectedPermissionId,
    permissionName,
    setPermissionName,
    menuPath,
    setMenuPath,
    searchTerm,
    setSearchTerm,
    isSubmitting,
    confirmacion,
    cerrarConfirmacion,
    filteredCount: filteredPermissions.length,
    groups,
    handlePermissionSelect,
    editPermission,
    handleSubmit,
    handleDelete,
    handleClear,
  };
}
