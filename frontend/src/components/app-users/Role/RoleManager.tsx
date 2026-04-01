import { useState, useEffect } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import RoleForm from "./RoleForm";
import PermissionForm from "./PermissionForm";

type Permission = {
  id: number;
  name: string;
  menu_path: string;
};

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function RoleManager({ setToast }: Props) {
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [activeView, setActiveView] = useState<"roles" | "permissions">("roles");
  const [loading, setLoading] = useState(true);

  const loadPermissions = async () => {
    setLoading(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.PERMISSIONS, {
        method: "GET",
      });

      if (res.ok) {
        setPermissions(res.data || []);
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
        {/* Header con título y navegación */}
        <div className="mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-3xl font-bold text-base-content flex items-center gap-3">
                <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                  <svg
                    className="w-7 h-7 text-primary"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                    />
                  </svg>
                </div>
                Gestión de Roles y Permisos
              </h1>
              <p className="text-base-content/60 mt-2">
                Administra roles y permisos del sistema de forma centralizada
              </p>
            </div>
          </div>

          {/* Navegación entre vistas */}
          <div className="tabs tabs-boxed bg-base-100 shadow-md p-1">
            <button
              className={`tab tab-lg flex-1 gap-2 transition-all ${
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
              className={`tab tab-lg flex-1 gap-2 transition-all ${
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
        </div>

        {/* Contenido principal */}
        <div className="animate-fadeIn">
          {loading ? (
            <div className="flex items-center justify-center min-h-[400px]">
              <div className="text-center">
                <span className="loading loading-spinner loading-lg text-primary"></span>
                <p className="mt-4 text-base-content/60">Cargando datos...</p>
              </div>
            </div>
          ) : activeView === "roles" ? (
            <RoleForm
              permissions={permissions}
              setToast={setToast}
            />
          ) : (
            <PermissionForm
              permissions={permissions}
              setToast={setToast}
              onPermissionChange={loadPermissions}
            />
          )}
        </div>
      </div>
    </div>
  );
}
