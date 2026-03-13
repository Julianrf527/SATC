import { useEffect, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TitleForm from "../../Label/TitleForm";
import NewRol from "../Role/NewRole";
import EditRol from "../Role/EditRole";
import NewPermission from "../Role/NewPermission";
import EditPermission from "../Role/EditPermission";

type Permission = { id: number; name: string; menu_path: string };

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};
export default function RolesPermisosPage({ setToast }: Props) {
  const [activeTab, setActiveTab] = useState<
    "nuevo-rol" | "editar-rol" | "nuevo-permiso" | "editar-permiso"
  >("nuevo-rol");
  const [permission, setPermission] = useState<Permission[]>([]);

  const loadPermissions = async () => {
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.PERMISSIONS, {
        method: "GET",
      });

      if (res.ok) {
        setPermission(res.data || []);
      } else {
        setToast({id: Date.now(), message: res.msg || "Error al cargar los permisos",type: "error"});
      }
    } catch (e) {
      /* console.error("Error al hacer fetch:", e); */
      setToast({id: Date.now(),message:"Error al cargar los permisos",type:"error"});
    }
  };

  useEffect(() => {
    loadPermissions();
  }, []);

  // Callback para refrescar permisos cuando se crea uno nuevo
  const handlePermissionCreated = () => {
    loadPermissions();
  };

  return (
    <div className="bg-base-200">
      <section className="w-full h-full flex justify-center items-start min-h-[calc(100vh-4rem)] overflow-hidden p-4">
        <div className="w-full max-w-4xl h-full">
          <div className="card bg-base-100 shadow-xl border border-base-300 w-full h-full">
            <div className="card-body px-6 py-6 flex flex-col h-full overflow-hidden">
              <TitleForm
                title="Gestión de Roles y Permisos"
                body="Crea nuevos roles, permisos y administra los existentes"
              />

              {/* Tabs */}
              <div
                role="tablist"
                className="tabs tabs-lifted justify-center mb-6 flex-shrink-0 flex-wrap"
              >
                <a
                  role="tab"
                  className={`tab text-sm font-medium ${
                    activeTab === "nuevo-rol"
                      ? "tab-active text-success"
                      : "hover:text-success"
                  }`}
                  onClick={() => setActiveTab("nuevo-rol")}
                >
                  <svg
                    className="w-4 h-4 mr-2"
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
                  Nuevo Rol
                </a>
                <a
                  role="tab"
                  className={`tab text-sm font-medium ${
                    activeTab === "editar-rol"
                      ? "tab-active text-warning"
                      : "hover:text-warning"
                  }`}
                  onClick={() => setActiveTab("editar-rol")}
                >
                  <svg
                    className="w-4 h-4 mr-2"
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
                  Editar Rol
                </a>
                <a
                  role="tab"
                  className={`tab text-sm font-medium ${
                    activeTab === "nuevo-permiso"
                      ? "tab-active text-primary"
                      : "hover:text-primary"
                  }`}
                  onClick={() => setActiveTab("nuevo-permiso")}
                >
                  <svg
                    className="w-4 h-4 mr-2"
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
                  Nuevo Permiso
                </a>
                <a
                  role="tab"
                  className={`tab text-sm font-medium ${
                    activeTab === "editar-permiso"
                      ? "tab-active text-info"
                      : "hover:text-info"
                  }`}
                  onClick={() => setActiveTab("editar-permiso")}
                >
                  <svg
                    className="w-4 h-4 mr-2"
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
                  Editar Permiso
                </a>
              </div>

              {/* Contenido de tabs con altura consistente */}
              <div className="flex-1 overflow-hidden min-h-0">
                {activeTab === "nuevo-rol" && (
                  <NewRol permission={permission} setToast={setToast} />
                )}

                {activeTab === "editar-rol" && (
                  <EditRol permission={permission} setToast={setToast} />
                )}

                {activeTab === "nuevo-permiso" && (
                  <NewPermission
                    setToast={setToast}
                    onPermissionCreated={handlePermissionCreated}
                  />
                )}

                {activeTab === "editar-permiso" && (
                  <EditPermission
                    setToast={setToast}
                    onPermissionUpdated={handlePermissionCreated}
                  />
                )}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
