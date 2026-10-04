import { useState, useEffect } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import RoleForm from "./RoleForm";
import type { Permiso } from "../../../types/userApp";
import PermissionForm from "./PermissionForm";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function RoleManager({ setToast }: Props) {
  const [permisoList, setPermisoList] = useState<Permiso[]>([]);
  const [activeView, setActiveView] = useState<"roles" | "permissions">(
    "roles",
  );
  const [loading, setLoading] = useState(true);

  const loadPermissions = async () => {
    setLoading(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.PERMISSIONS, {
        method: "GET",
      });

      if (res.ok) {
        setPermisoList(res.data || []);
      } else {
        setToast({
          id: Date.now(),
          message: res.msg || "Error al cargar los permisos",
          type: "error",
        });
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: "Error al cargar los permisos",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPermissions();
  }, []);

  return (
    <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="card bg-base-100 shadow-xl border border-base-300 flex flex-col h-[calc(100vh-8rem)] overflow-hidden">
          {/* Navegación entre vistas: pestañas como encabezado de la misma caja */}
          <div className="grid grid-cols-2 border-b border-base-300 flex-none">
            <button
              className={`flex items-center justify-center gap-2 py-4 font-semibold border-r border-base-300 transition-colors ${
                activeView === "roles"
                  ? "bg-green-600 text-white"
                  : "hover:bg-base-200"
              }`}
              onClick={() => setActiveView("roles")}
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
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                />
              </svg>
              Gestión de Roles
            </button>
            <button
              className={`flex items-center justify-center gap-2 py-4 font-semibold transition-colors ${
                activeView === "permissions"
                  ? "bg-blue-600 text-white"
                  : "hover:bg-base-200"
              }`}
              onClick={() => setActiveView("permissions")}
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
                  d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                />
              </svg>
              Gestión de Permisos
            </button>
          </div>

          {/* Contenido principal */}
          <div className="flex-1 min-h-0 flex flex-col">
            {loading ? (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <span className="loading loading-spinner loading-lg text-primary"></span>
                  <p className="mt-4 text-base-content/60">Cargando datos...</p>
                </div>
              </div>
            ) : activeView === "roles" ? (
              <RoleForm permisoList={permisoList} setToast={setToast} />
            ) : (
              <PermissionForm
                permisoList={permisoList}
                setToast={setToast}
                onPermissionChange={loadPermissions}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
