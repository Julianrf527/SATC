import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useState, useEffect } from "react";
import { toastService } from "./utils/toastService";
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
import GestionExpedienteLayout from "./components/app-sancionatorio/Layout/GestionExpedienteLayout";
import ConsultaExpedieneLayout from "./components/app-sancionatorio/Layout/ConsultaExpedieneLayout";
import EncargadoExpedienteLayout from "./components/app-sancionatorio/Layout/EncargadoExpedienteLayout";
import AlertasExpediente from "./components/app-sancionatorio/Layout/AlertasExpediente";
import ExpedienteLogLayout from "./components/app-sancionatorio/Layout/ExpedienteLogLayout";
import GestionInfraccionLayout from "./components/app-infraccion/Layout/GestionInfraccionLayout";
import ConsultaInfraccionLayout from "./components/app-infraccion/Layout/ConsultaInfraccionLayout";
import EncargadoInfraccionLayout from "./components/app-infraccion/Layout/EncargadoInfraccionLayout";
import InfraccionLogLayout from "./components/app-infraccion/Layout/InfraccionLogLayout";
import AsignarInformes from "./components/app-infraccion/Layout/AsignarInformes";
import MisInformes from "./components/app-infraccion/Layout/MisInformes";
import AlertasInfraccionLayout from "./components/app-infraccion/Layout/AlertasInfraccionLayout";
import InvolucradoLogLayout from "./components/app-involved/Layout/InvolucradoLogLayout";
import ManageInvolvedLayout from "./components/app-involved/Layout/ManageInvolvedLayout";
import DocumentPage from "./components/app-documentos/layout/DocumentosPage";
import ErrorBoundary from "./components/Common/ErrorBoundary";

type RouteConfig = {
  path: string;
  component: React.ComponentType<any>;
  props?: Record<string, any>;
};

const inferPermissionFromPath = (path: string): string | string[] => {
  // Las claves deben coincidir con los permisos sembrados en seeds.py del backend.
  const pathToPermissionMap: Record<string, string | string[]> = {
    // === ADMINISTRACIÓN ===
    "/user/role": "admin_roles_y_permisos",
    "/user/add": "admin_registrar_usuarios",
    "/user/manage": "admin_gestionar_usuarios",

    // === SANCIONATORIO ===
    "/file/manage": "sancionatorio_gestionar",
    "/file/consult": "sancionatorio_consultar",
    "/file/alerts": "sancionatorio_alertas",
    "/file/assign_manage": "sancionatorio_asignar",

    // === INVOLUCRADOS ===
    "/involved/manage": "involucrado_gestionar",

    // === DOCUMENTOS ===
    "/document/manage": "documento_gestionar",

    // === AUDITORÍA ===
    "/audit/users": "auditoria_usuarios",
    "/audit/files": "auditoria_expedientes",
    "/audit/involved": "auditoria_involucrados",
    "/audit/infractions": "auditoria_infracciones",

    "/infraction/manage": "infraccion_gestionar",
    "/infraction/consult": "infraccion_consultar",
    "/infraction/alerts": "infraccion_alertas",
    "/infraction/assign_manage": "infraccion_asignar",
    "/infraction/reports": "infraccion_asignar_informes",
    "/infraction/my-reports": ["infraccion_informes_subir", "infraccion_informes_revisar"],
  };

  const permission = pathToPermissionMap[path];

  if (!permission) {
    console.warn(`No se encontró permiso para el path: ${path}`);
    return `unknown_permission_${path.replace(/[^a-zA-Z0-9]/g, "_")}`;
  }

  return permission;
};

const ProtectedRoute = ({
  component: Component,
  path,
  props = {},
  setToast,
}: {
  component: React.ComponentType<any>;
  path: string;
  props?: Record<string, any>;
  setToast: React.Dispatch<
    React.SetStateAction<{
      id: number;
      message: string;
      type: "success" | "error";
    } | null>
  >;
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
  
  // Registrar el handler global permite lanzar toasts sin prop drilling.
  useEffect(() => {
    toastService.setHandler(setToast);
  }, []);

  useEffect(() => {
    const savedTheme = localStorage.getItem("theme") as
      | "emerald"
      | "dark"
      | null;
    if (savedTheme) {
      setTheme(savedTheme);
    }
  }, [setTheme]);

  // No se declara permiso: se infiere del path vía inferPermissionFromPath.
  const protectedRoutes: RouteConfig[] = [
    // === AUDITORÍA ===
    { path: "/audit/users", component: UserLogLayout },
    { path: "/audit/files", component: ExpedienteLogLayout },
    { path: "/audit/infractions", component: InfraccionLogLayout },
    { path: "/audit/involved", component: InvolucradoLogLayout },

    // === ADMINISTRACIÓN ===
    { path: "/user/add", component: SignUpLayout },
    { path: "/user/manage", component: ManageUserLayout },
    { path: "/user/role", component: RoleLayout },

    // === EXPEDIENTES ===
    { path: "/file/manage", component: GestionExpedienteLayout },
    { path: "/file/consult", component: ConsultaExpedieneLayout },
    { path: "/file/alerts", component: AlertasExpediente },
    { path: "/file/assign_manage", component: EncargadoExpedienteLayout },

    // === INVOLUCRADOS ===
    { path: "/involved/manage", component: ManageInvolvedLayout },

    // === DOCUMENTOS ===
    { path: "/document/manage", component: DocumentPage },

    // === INFRACCIONES ===
    { path: "/infraction/manage", component: GestionInfraccionLayout },
    { path: "/infraction/consult", component: ConsultaInfraccionLayout },
    { path: "/infraction/assign_manage", component: EncargadoInfraccionLayout },
    { path: "/infraction/reports", component: AsignarInformes },
    { path: "/infraction/my-reports", component: MisInformes },
    { path: "/infraction/alerts", component: AlertasInfraccionLayout },
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
      <ErrorBoundary>
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
                    <ErrorBoundary key={route.path}>
                      <ProtectedRoute
                        component={route.component}
                        path={route.path}
                        props={route.props}
                        setToast={setToast}
                      />
                    </ErrorBoundary>
                  }
                />
              ))}
            </Route>

            {/* cualquier ruta desconocida fuera de "/" redirige a main */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </ErrorBoundary>
    </div>
  );
}

export default App;
