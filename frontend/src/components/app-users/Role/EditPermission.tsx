import Input from "../../Input/Input";
import { useEffect, useState, useRef } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import ConfirmDeleteRolePermissionModal from "./ConfirmDeleteRolePermissionModa";

type Permission = { id: number; name: string; menu_path: string };

type Props = {
  setToast: (toast: {
    id: number; 
    message: string; 
    type: "success" | "error";
    }) => void;
  onPermissionUpdated?: () => void;
};

export default function EditPermission({
  setToast,
  onPermissionUpdated,
}: Props) {
  const permissionNameRef = useRef<HTMLInputElement>(null);
  const menuPathRef = useRef<HTMLInputElement>(null);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [selectedPermissionId, setSelectedPermissionId] = useState("0");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handlePermissionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const permissionTemp = permissions.find(
      (p) => p.id === Number(e.target.value)
    );
    setSelectedPermissionId(e.target.value);

    if (permissionNameRef.current) {
      permissionNameRef.current.value = permissionTemp
        ? permissionTemp.name
        : "";
    }
    if (menuPathRef.current) {
      menuPathRef.current.value = permissionTemp
        ? permissionTemp.menu_path
        : "";
    }
  };

  const onEditPermission = async () => {
    if (
      !permissionNameRef.current ||
      permissionNameRef.current.value.trim() === ""
    ) {
      setToast({id: Date.now(),message:"El nombre del permiso es obligatorio",type:"error"});
      return;
    }
    if (!menuPathRef.current || menuPathRef.current.value.trim() === "") {
      setToast({id: Date.now(),message:"El menu_path es obligatorio",type:"error"});
      return;
    }
    if (selectedPermissionId === "0" || selectedPermissionId === "") {
      setToast({id: Date.now(),message:"Debe seleccionar un permiso",type:"error"});
      return;
    }

    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.PERMISSION_UPDATE(selectedPermissionId),
        {
          method: "PUT",
          body: JSON.stringify({
            name: permissionNameRef.current.value,
            menu_path: menuPathRef.current.value,
          }),
        }
      );

      if (res.ok) {
        setToast({id: Date.now(),message:"Permiso actualizado correctamente",type:"success"});

        const updatedName = permissionNameRef.current.value;
        const updatedPath = menuPathRef.current.value;

        setPermissions((prev) =>
          prev.map((p) =>
            p.id === Number(selectedPermissionId)
              ? {
                  ...p,
                  name: updatedName,
                  menu_path: updatedPath,
                }
              : p
          )
        );

        setSelectedPermissionId("0");
        if (permissionNameRef.current) permissionNameRef.current.value = "";
        if (menuPathRef.current) menuPathRef.current.value = "";

        if (onPermissionUpdated) {
          onPermissionUpdated();
        }
      } else {
        setToast({id: Date.now(),message:res.detail || "Error al actualizar el permiso",type:"error"});
      }
    } catch (e) {
      console.error("Error al hacer fetch:", e);
      setToast({id: Date.now(),message:"Error al actualizar el permiso",type:"error"});
    }
  };

  const onDeletePermission = async () => {
    if (selectedPermissionId === "0" || selectedPermissionId === "") {
      setToast({id: Date.now(),message:"Debe seleccionar un permiso",type:"error"});
      return;
    }

    setShowDeleteModal(true);
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);

    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.PERMISSION_DELETE(selectedPermissionId),
        {
          method: "DELETE",
        }
      );

      if (res.ok) {
        setToast({id: Date.now(),message:"Permiso eliminado correctamente", type:"success"});
        setPermissions((prev) =>
          prev.filter((p) => p.id !== Number(selectedPermissionId))
        );

        setSelectedPermissionId("0");
        if (permissionNameRef.current) permissionNameRef.current.value = "";
        if (menuPathRef.current) menuPathRef.current.value = "";

        if (onPermissionUpdated) {
          onPermissionUpdated();
        }
      } else {
        setToast({id: Date.now(),message: res.detail || "Error al eliminar el permiso",type:"error"});
      }
    } catch (e) {
      console.error("Error al hacer fetch:", e);
      setToast({id: Date.now(), message:"Error al eliminar el permiso",type:"error"});
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  useEffect(() => {
    async function getPermissions() {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.PERMISSIONS, {
          method: "GET",
        });
        if (res.ok) {
          setPermissions(res.data || []);
        } else {
          setToast({id: Date.now(),message:"Error al cargar los permisos",type:"error"});
        }
      } catch (e) {
        console.error("Error al hacer fetch:", e);
        setToast({id: Date.now(),message:"Error al cargar los permisos",type:"error"});
      }
    }
    getPermissions();
  }, []);

  return (
    <div className="card bg-base-100 shadow-md border border-base-300 h-full flex flex-col">
      <ConfirmDeleteRolePermissionModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleConfirmDelete}
        type="permiso"
        itemName={
          permissions.find((p) => p.id === Number(selectedPermissionId))?.name
        }
        isDeleting={isDeleting}
      />

      <div className="card-body flex flex-col h-full">
        {/* Header - Altura fija */}
        <div className="flex items-center gap-3 mb-6 flex-shrink-0">
          <div className="w-10 h-10 bg-info/10 rounded-lg flex items-center justify-center">
            <svg
              className="w-5 h-5 text-info"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-xl font-bold">Editar Permiso</h3>
            <p className="text-sm text-base-content/60">
              Modifica o elimina permisos existentes
            </p>
          </div>
        </div>

        {/* Selector - Altura fija */}
        <div className="mb-4 flex-shrink-0">
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Seleccionar permiso
              </span>
            </label>
            <select
              className="select select-bordered w-full"
              onChange={handlePermissionChange}
              value={selectedPermissionId}
            >
              <option value="0">Seleccione un permiso</option>
              {permissions.map((permission) => (
                <option key={permission.id} value={permission.id}>
                  {permission.name} - {permission.menu_path}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Formulario - Altura variable según selección */}
        {selectedPermissionId !== "0" && (
          <div className="space-y-4 mb-4 flex-shrink-0">
            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Nombre del permiso
                </span>
              </label>
              <Input
                placeholder="Nombre del Permiso"
                inputRef={permissionNameRef}
              />
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">Ruta del menú</span>
              </label>
              <Input placeholder="Ruta del menú" inputRef={menuPathRef} />
              <label className="label">
                <span className="label-text-alt text-base-content/60">
                  Define la ruta de acceso en el sistema
                </span>
              </label>
            </div>
          </div>
        )}

        {/* Espacio reservado para mantener consistencia - Altura fija (mínima) */}
        <div className="h-8 mb-4 flex-shrink-0"></div>

        {/* Contenido dinámico - Espacio flexible */}
        <div className="flex-1 min-h-0 mb-6">
          {selectedPermissionId !== "0" ? (
            <div className="rounded-lg border border-base-300 h-full flex items-center justify-center bg-info/5">
              <div className="text-center py-12 px-4">
                <div className="w-16 h-16 bg-info/10 rounded-full flex items-center justify-center mb-4 mx-auto">
                  <svg
                    className="w-8 h-8 text-info"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-base-content/70 mb-2">
                  Permiso seleccionado
                </h3>
                <div className="text-sm text-base-content/60 space-y-2 max-w-md mx-auto">
                  <p>
                    Modifica los campos anteriores para actualizar el permiso.
                  </p>
                  <div className="mt-4 bg-warning/10 rounded-lg p-3 border border-warning/20">
                    <p className="text-warning font-medium">
                      ⚠️ Al eliminar un permiso, asegúrate de que no esté
                      asignado a ningún rol
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-lg border border-base-300 h-full flex items-center justify-center">
              <div className="text-center py-12">
                <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4 mx-auto">
                  <svg
                    className="w-8 h-8 text-info"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                    />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-base-content/70 mb-2">
                  Selecciona un permiso para editar
                </h3>
                <p className="text-sm text-base-content/60">
                  Elige un permiso de la lista para modificar sus datos
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Botones de acción - Altura fija */}
        <div className="flex-shrink-0">
          {selectedPermissionId !== "0" && (
            <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
              <button
                onClick={onDeletePermission}
                className="btn btn-error btn-outline gap-2"
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
              <button onClick={onEditPermission} className="btn btn-info gap-2">
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
                Actualizar Permiso
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
