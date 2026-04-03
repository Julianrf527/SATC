import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useState, useEffect } from "react";
import Toast from "./components/Toast";
import LoginPage from "./pages/LoginPage";
import RecoverPage from "./pages/RecoverPage";
import MainLayout from "./layout/MainLayout";
import WelcomeLayout from "./layout/WelcomeLayout";
import SignUpLayout from "./components/app-users/Layout/SignUpLayout";
import ManageUserLayout from "./components/app-users/Layout/ManageUserLayout";
import RoleLayout from "./components/app-users/Layout/RoleLayout";
import UserLogLayout from "./components/app-users/Layout/UserLogLayout";
import ProfileLayout from "./components/app-users/Layout/ProfileLayout";
import RequirePermission from "./context/RequirePermission";
import FileManageLayout from "./components/app-sancionatorio/Layout/GestionExpedienteLayout";
import FileViewLayout from "./components/app-sancionatorio/Layout/ConsultaExpedieneLayout";
import ManagerFilesLayout from "./components/app-sancionatorio/Layout/EncargadoExpedienteLayout";
import AlertsLayout from "./components/app-sancionatorio/Layout/AlertsLayout";
import FileLogLayout from "./components/app-sancionatorio/Layout/ExpedienteLogLayout";
import ManageInvolvedLayout from "./components/app-involved/Layout/ManageInvolvedLayout";
import DocumentPage from "./components/app-documentos/layout/DocumentosPage";
//infracciones Compoents




// Configuración simplificada de rutas (solo path y componente)
type RouteConfig = {
  path: string;
  component: React.ComponentType<any>;
  props?: Record<string, any>;
};

// Inferencia automática de permisos basada en el path
const inferPermissionFromPath = (path: string): string => {
  // Mapeo de paths a permisos siguiendo exactamente el patrón actualizado de seeds.py
  const pathToPermissionMap: Record<string, string> = {
    // === ADMINISTRACIÓN ===
    "/user/role": "admin_roles",
    "/user/add": "admin_crear_usuarios",
    "/user/manage": "admin_gestionar_usuarios",

    // === EXPEDIENTES ===
    "/file/manage": "expediente_gestionar",
    "/file/consult": "expediente_consultar",
    "/file/alerts": "expediente_alertas",
    "/file/assign_manage": "expediente_asignar",
    
    // === INVOLUCRADOS ===
    "/involved/manage": "involucrado_gestionar",

    // === DOCUMENTOS ===
    "/document/manage": "documento_gestionar",

    // === AUDITORÍA ===
    "/audit/users": "auditoria_usuarios",
    "/audit/files": "auditoria_expedientes",
    "/audit/involved": "auditoria_involucrados",

    "/infraction/manage": "infracciones_gestionar",
    "/infraction/consult": "infracciones_consultar",
    "/infraction/alerts": "infracciones_alertas",
    "/infraction/assign_manage": "infracciones_asignar"

  };

  const permission = pathToPermissionMap[path];

  if (!permission) {
    console.warn(`No se encontró permiso para el path: ${path}`);
    return `unknown_permission_${path.replace(/[^a-zA-Z0-9]/g, '_')}`;
  }

  return permission;
};

// Componente helper para rutas protegidas con inferencia automática
const ProtectedRoute = ({
  component: Component,
  path,
  props = {},
  setToast
}: {
  component: React.ComponentType<any>;
  path: string;
  props?: Record<string, any>;
  setToast: React.Dispatch<React.SetStateAction<{ id: number; message: string; type: "success" | "error" } | null>>;
}) => {
  const permission = inferPermissionFromPath(path);

  return (
    <RequirePermission required={permission}>
      <Component setToast={setToast} {...props} />
    </RequirePermission>
  );
};

function App() {
  const [theme, setTheme] = useState<"emerald" | "dark">("emerald");
  const [toast, setToast] = useState<{
    id: number;
    message: string;
    type: "success" | "error";
  } | null>(null);

  // === cargar tema guardado en localStorage al inicio ===
  useEffect(() => {
    const savedTheme = localStorage.getItem("theme") as
      | "emerald"
      | "dark"
      | null;
    if (savedTheme) {
      setTheme(savedTheme);
    }
  }, [setTheme]);

  // Configuración simplificada - permisos se infieren automáticamente del path
  const protectedRoutes: RouteConfig[] = [
    // === AUDITORÍA ===
    { path: "/audit/users", component: UserLogLayout },
    { path: "/audit/files", component: FileLogLayout },

    // === ADMINISTRACIÓN ===
    { path: "/user/add", component: SignUpLayout },
    { path: "/user/manage", component: ManageUserLayout },
    { path: "/user/role", component: RoleLayout },

    // === EXPEDIENTES ===
    { path: "/file/manage", component: FileManageLayout },
    { path: "/file/consult", component: FileViewLayout },
    { path: "/file/alerts", component: AlertsLayout },
    { path: "/file/assign_manage", component: ManagerFilesLayout },
    
    // === INVOLUCRADOS ===
    { path: "/involved/manage", component: ManageInvolvedLayout },

    // === DOCUMENTOS ===
    { path: "/document/manage", component: DocumentPage },

    // === INFRACCIONES ===
    { path: "/infraction/manage", component: InfractionManageLayout },
    { path: "/infraction/consult", component: InfractionViewLayout },
    { path: "/infraction/assign_manage", component: InfractionAssignLayout }

  ];

  return (
    <div data-theme={theme}>
      {toast && (
        <Toast
          id={toast.id}
          message={toast.message}
          type={toast.type}
          duration={4000}
        />
      )}
      <BrowserRouter>
        <Routes>
          {/* páginas públicas */}
          <Route path="/login" element={<LoginPage theme={theme} />} />
          <Route path="/recover" element={<RecoverPage theme={theme} />} />

          {/* páginas privadas */}
          <Route
            path=""
            element={<MainLayout setTheme={setTheme} setToast={setToast} />}
          >
            {/* página de inicio (sin restricciones) */}
            <Route index element={<WelcomeLayout theme={theme} />} />

            {/* perfil (sin restricciones) */}
            <Route
              path="/profile"
              element={<ProfileLayout setToast={setToast} />}
            />

            {/* rutas protegidas con inferencia automática de permisos */}
            {protectedRoutes.map((route) => (
              <Route
                key={route.path}
                path={route.path}
                element={
                  <ProtectedRoute
                    component={route.component}
                    path={route.path}
                    props={route.props}
                    setToast={setToast}
                  />
                }
              />
            ))}
          </Route>

          {/* cualquier ruta desconocida fuera de "/" redirige a main */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;