import { useMemo, useState } from "react";
import type { Permiso, SetToast } from "../../types";
import {
  useDeleteRolMutation,
  useRolesConPermisosQuery,
  useSaveRolMutation,
} from "../../api/roles";
import { apiErrorMessage } from "../../api/errors";
import { useConfirmacion } from "../useConfirmacion";
import { generateCategories, permissionLabel } from "./permissionCategories";
import {
  agregarPermiso,
  alternarCategoria,
  estaBloqueado,
  incumplimientos as calcularIncumplimientos,
  quitarConDependientes,
  requisitosFaltantes,
} from "./permissionDependencies";

/** Largo máximo del nombre del rol: columna `rol.nombre` es varchar(20). */
export const ROL_NOMBRE_MAX = 20;

/** Estado de un permiso en el selector según las dependencias. */
export type EstadoPermiso = {
  /** No marcado y le falta algún requerido: checkbox deshabilitado. */
  bloqueado: boolean;
  /** Etiquetas legibles de los requeridos que no están marcados. */
  faltan: string[];
};

/** Lista legible "A, B y C". */
const enumerar = (items: string[]) =>
  items.length <= 1
    ? items.join("")
    : `${items.slice(0, -1).join(", ")} y ${items[items.length - 1]}`;

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
  /** Aviso de permisos quitados en cascada al desmarcar un requerido. */
  const [avisoCascada, setAvisoCascada] = useState<string | null>(null);
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

  // Permisos marcados sin todos sus requeridos (p. ej. un rol creado antes de
  // existir las dependencias): se muestran y bloquean el guardado.
  const incumplimientos = useMemo(
    () =>
      calcularIncumplimientos(selectedPermissions, permisoList).map((i) => ({
        permiso: permissionLabel(i.permiso.nombre),
        faltan: i.faltan.map(permissionLabel),
      })),
    [selectedPermissions, permisoList],
  );

  const getEstadoPermiso = (permiso: Permiso): EstadoPermiso => ({
    bloqueado: estaBloqueado(permiso, selectedPermissions, permisoList),
    faltan: requisitosFaltantes(permiso, selectedPermissions, permisoList).map(permissionLabel),
  });

  const avisarQuitados = (quitados: number[]) => {
    if (quitados.length === 0) return;
    const nombres = permisoList
      .filter((p) => quitados.includes(p.id))
      .map((p) => permissionLabel(p.nombre));
    setAvisoCascada(
      `Se ${quitados.length === 1 ? "quitó" : "quitaron"} ${enumerar(nombres)} porque ` +
        `${quitados.length === 1 ? "depende" : "dependen"} de un permiso desmarcado.`,
    );
  };

  const resetForm = () => {
    setRoleName("");
    setSelectedPermissions([]);
    setSelectedRoleId("");
    setAvisoCascada(null);
  };

  const handleRoleSelect = (roleId: string) => {
    setSelectedRoleId(roleId);
    setAvisoCascada(null);
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
    if (selectedPermissions.includes(permissionId)) {
      const r = quitarConDependientes(selectedPermissions, [permissionId], permisoList);
      setSelectedPermissions(r.seleccion);
      avisarQuitados(r.quitados);
    } else {
      // Bloqueado (le falta un requerido): agregarPermiso no lo marca.
      setSelectedPermissions(agregarPermiso(selectedPermissions, permissionId, permisoList));
    }
  };

  const toggleCategoryPermissions = (prefix: string) => {
    const categoryPermissions = permisoList
      .filter((p) => p.nombre.startsWith(prefix))
      .map((p) => p.id);

    const r = alternarCategoria(selectedPermissions, categoryPermissions, permisoList);
    setSelectedPermissions(r.seleccion);
    avisarQuitados(r.quitados);
  };

  const getFilteredPermissions = (prefix: string) => {
    const term = searchTerm.toLowerCase();
    return permisoList.filter(
      (p) =>
        p.nombre.startsWith(prefix) &&
        (searchTerm === "" ||
          p.nombre.toLowerCase().includes(term) ||
          (p.menu_path ?? "").toLowerCase().includes(term) ||
          (p.descripcion ?? "").toLowerCase().includes(term)),
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

    if (roleName.trim().length > ROL_NOMBRE_MAX) {
      setToast({
        id: Date.now(),
        message: `El nombre del rol no puede exceder ${ROL_NOMBRE_MAX} caracteres`,
        type: "error",
      });
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

    if (incumplimientos.length > 0) {
      setToast({
        id: Date.now(),
        message: "Hay permisos sin sus requeridos: corrija el rol antes de guardar",
        type: "error",
      });
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
    incumplimientos,
    getEstadoPermiso,
    avisoCascada,
    cerrarAvisoCascada: () => setAvisoCascada(null),
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
