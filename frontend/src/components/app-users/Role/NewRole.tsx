import { apiCall, API_CONFIG } from "../../../utils/api";
import React from "react";
import Input from "../../Input/Input";

type Props = {
  permission: { id: number; name: string; menu_path: string }[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function NewRole({ permission, setToast }: Props) {
  const roleNameRef = React.useRef<HTMLInputElement>(null);
  const [permissionList, setPermissionList] = React.useState<number[]>([]);

  const togglePermission = (id: number) => {
    setPermissionList((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const toggleAddRol = async () => {
    if (!roleNameRef.current || roleNameRef.current.value.trim() === "") {
      setToast({id: Date.now(),message:"El nombre del rol es obligatorio",type:"error"});
      return;
    }
    if (permissionList.length === 0) {
      setToast({id: Date.now(),message:"Debe seleccionar al menos un permiso",type: "error"});
      return;
    }
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.ROL_ADD, {
        method: "POST",
        body: JSON.stringify({
          name: roleNameRef.current.value,
          permission: permissionList,
        }),
      });
      if (res.ok) {
        setToast({id: Date.now(),message:"Rol creado correctamente",type:"success"});
        if (roleNameRef.current) roleNameRef.current.value = "";
        setPermissionList([]);
      } else {
        setToast({id: Date.now(),message:res.detail || "Error al crear el rol",type:"error"});
      }
    } catch (e) {
      console.error("Error al hacer fetch:", e);
      setToast({id: Date.now(),message:"Error al crear el rol",type:"error"});
    }
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300 h-full flex flex-col">
      <div className="card-body flex flex-col h-full">
        {/* Header - Altura fija */}
        <div className="flex items-center gap-3 mb-6 flex-shrink-0">
          <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
            <svg
              className="w-5 h-5 text-success"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M8.8 4.354a4 4 0 1 0 0 8a4 4 0 1 0 0-8M15 23H3v-1a6 6 0 0 1 12 0v1zm0 0h6v-1a6 6 0 0 0-9-5.197m6-9a2.5 2.5 0 1 1-5 0a2.5 2.5 0 0 1 5 0z"
              />
            </svg>
          </div>
          <div>
            <h3 className="text-xl font-bold">Nuevo Rol</h3>
            <p className="text-sm text-base-content/60">
              Asigna permisos al nuevo rol
            </p>
          </div>
        </div>

        {/* Input del nombre del rol - Altura fija */}
        <div className="mb-4 flex-shrink-0">
          <Input placeholder="Nombre del Rol" inputRef={roleNameRef} />
        </div>

        {/* Contador de permisos - Altura fija (mínima) */}
        <div className="h-8 mb-4 flex-shrink-0">
          {permissionList.length > 0 && (
            <div className="flex items-center gap-2 text-sm text-base-content/70 px-2">
              <svg
                className="w-4 h-4 text-info"
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
              <span>
                {permissionList.length} permiso
                {permissionList.length !== 1 ? "s" : ""} seleccionado
                {permissionList.length !== 1 ? "s" : ""}
              </span>
            </div>
          )}
        </div>

        {/* Tabla de permisos - Espacio flexible */}
        <div className="overflow-x-auto rounded-lg border border-base-300 mb-6 flex-1 min-h-0">
          <div className="overflow-y-auto h-full">
            <table className="table table-zebra w-full">
              <thead className="sticky top-0 bg-base-200 z-10">
                <tr>
                  <th className="text-sm font-semibold">Permiso</th>
                  <th className="text-sm font-semibold w-32 text-center">
                    Acción
                  </th>
                </tr>
              </thead>
              <tbody>
                {permission.length > 0 ? (
                  permission.map((p) => (
                    <tr key={p.id} className="hover">
                      <td className="text-sm">{p.name}</td>
                      <td className="text-center">
                        <button
                          onClick={() => togglePermission(p.id)}
                          className={`btn btn-sm gap-2 ${
                            permissionList.includes(p.id)
                              ? "btn-error btn-outline"
                              : "btn-success text-white"
                          }`}
                        >
                          {permissionList.includes(p.id) ? (
                            <>
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
                                  d="M6 18L18 6M6 6l12 12"
                                />
                              </svg>
                              Quitar
                            </>
                          ) : (
                            <>
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
                                  d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                                />
                              </svg>
                              Agregar
                            </>
                          )}
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={2} className="text-center py-8">
                      <div className="flex flex-col items-center gap-2">
                        <svg
                          className="w-12 h-12 text-base-content/30"
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
                        <p className="text-base-content/60 text-sm">
                          No hay permisos disponibles
                        </p>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Botón de crear - Altura fija */}
        <div className="flex justify-end pt-4 border-t border-base-300 flex-shrink-0">
          <button
            onClick={toggleAddRol}
            className="btn btn-success text-white gap-2"
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
            Crear Rol
          </button>
        </div>
      </div>
    </div>
  );
}
