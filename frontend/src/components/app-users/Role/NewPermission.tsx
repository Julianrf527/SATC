import { apiCall, API_CONFIG } from "../../../utils/api";
import React from "react";
import Input from "../../Common/Input/Input";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  onPermissionCreated?: () => void;
};

export default function NewPermission({
  setToast,
  onPermissionCreated,
}: Props) {
  const permissionNameRef = React.useRef<HTMLInputElement>(null);
  const menuPathRef = React.useRef<HTMLInputElement>(null);

  const handleCreatePermission = async () => {
    if (
      !permissionNameRef.current ||
      permissionNameRef.current.value.trim() === ""
    ) {
      setToast({
        id: Date.now(),
        message: "El nombre del permiso es obligatorio",
        type: "error",
      });
      return;
    }
    if (!menuPathRef.current || menuPathRef.current.value.trim() === "") {
      setToast({
        id: Date.now(),
        message: "El menu_path es obligatorio",
        type: "error",
      });
      return;
    }

    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.PERMISSION_ADD, {
        method: "POST",
        body: JSON.stringify({
          name: permissionNameRef.current.value,
          menu_path: menuPathRef.current.value,
        }),
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Permiso creado correctamente",
          type: "success",
        });
        if (permissionNameRef.current) permissionNameRef.current.value = "";
        if (menuPathRef.current) menuPathRef.current.value = "";

        if (onPermissionCreated) {
          onPermissionCreated();
        }
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al crear el permiso",
          type: "error",
        });
      }
    } catch (e) {
      /* console.error("Error al hacer fetch:", e); */
      setToast({
        id: Date.now(),
        message: "Error al crear el permiso",
        type: "error",
      });
    }
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300 h-full flex flex-col">
      <div className="card-body flex flex-col h-full">
        {/* Header - Altura fija */}
        <div className="flex items-center gap-3 mb-6 flex-shrink-0">
          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
            <svg
              className="w-5 h-5 text-primary"
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
          <div>
            <h3 className="text-xl font-bold">Nuevo Permiso</h3>
            <p className="text-sm text-base-content/60">
              Crea un nuevo permiso para asignar a roles
            </p>
          </div>
        </div>

        {/* Formulario - Altura fija */}
        <div className="space-y-4 mb-4 flex-shrink-0">
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">Nombre del permiso</span>
            </label>
            <Input
              placeholder="Ej: Gestionar usuarios"
              inputRef={permissionNameRef}
            />
          </div>

          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">Ruta del menú</span>
            </label>
            <Input placeholder="Ej: /admin/usuarios" inputRef={menuPathRef} />
            <label className="label">
              <span className="label-text-alt text-base-content/60">
                Define la ruta de acceso en el sistema
              </span>
            </label>
          </div>
        </div>

        {/* Espacio reservado para mantener consistencia con otros tabs - Altura fija (mínima) */}
        <div className="h-8 mb-4 flex-shrink-0"></div>

        {/* Área de información - Espacio flexible */}
        <div className="flex-1 min-h-0 mb-6">
          <div className="rounded-lg border border-base-300 h-full flex items-center justify-center bg-base-200/30">
            <div className="text-center py-12 px-4">
              <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4 mx-auto">
                <svg
                  className="w-8 h-8 text-primary"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-base-content/70 mb-2">
                Información sobre permisos
              </h3>
              <div className="text-sm text-base-content/60 space-y-2 max-w-md mx-auto">
                <p>
                  Los permisos son acciones específicas que pueden ser asignadas
                  a diferentes roles.
                </p>
                <p>
                  Una vez creado, el permiso estará disponible para ser asociado
                  a cualquier rol en el sistema.
                </p>
                <div className="mt-4 bg-info/10 rounded-lg p-3 border border-info/20">
                  <p className="text-info font-medium">
                    Asegúrate de usar nombres descriptivos y rutas únicas
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Botón de crear - Altura fija */}
        <div className="flex justify-end pt-4 border-t border-base-300 flex-shrink-0">
          <button
            onClick={handleCreatePermission}
            className="btn text-white btn-success gap-2"
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
                d="M12 6v6m0 0v6m0-6h6m-6 0H6"
              />
            </svg>
            Crear Permiso
          </button>
        </div>
      </div>
    </div>
  );
}
