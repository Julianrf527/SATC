import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { lazy, Suspense, useState, useEffect } from "react";
import { toastService } from "@shared/lib/toastService";
import Toast from "@shared/ui/Toast";
import LoadingBar from "@shared/ui/LoadingBar";
import ErrorBoundary from "@shared/ui/ErrorBoundary";
import { useTheme } from "@shared/hooks/useTheme";
import MainLayout from "./layout/MainLayout";
import WelcomeLayout from "./layout/WelcomeLayout";
import RequirePermission from "./router/RequirePermission";

// Code-splitting: cada pantalla enrutada es un chunk propio que se descarga
// al navegar a ella. Las pantallas de un mismo módulo comparten sus chunks
// internos (Rollup extrae lo común automáticamente).

// === app-users ===
const LoginPage = lazy(() => import("@modules/app-users/auth/LoginPage"));
const RecoverPage = lazy(() => import("@modules/app-users/auth/RecoverPage"));
const SignUpLayout = lazy(() => import("@modules/app-users/layout/SignUpLayout"));
const ManageUserLayout = lazy(() => import("@modules/app-users/layout/ManageUserLayout"));
const RoleLayout = lazy(() => import("@modules/app-users/layout/RoleLayout"));
const UserLogLayout = lazy(() => import("@modules/app-users/layout/UserLogLayout"));
const ProfileLayout = lazy(() => import("@modules/app-users/layout/ProfileLayout"));
// === app-sancionatorio ===
const GestionExpedienteLayout = lazy(() => import("@modules/app-sancionatorio/layout/GestionExpedienteLayout"));
const ConsultaExpedieneLayout = lazy(() => import("@modules/app-sancionatorio/layout/ConsultaExpedieneLayout"));
const EncargadoExpedienteLayout = lazy(() => import("@modules/app-sancionatorio/layout/EncargadoExpedienteLayout"));
const AlertasExpediente = lazy(() => import("@modules/app-sancionatorio/layout/AlertasExpediente"));
const ExpedienteLogLayout = lazy(() => import("@modules/app-sancionatorio/layout/ExpedienteLogLayout"));
// === app-infraccion ===
const GestionInfraccionLayout = lazy(() => import("@modules/app-infraccion/layout/GestionInfraccionLayout"));
const ConsultaInfraccionLayout = lazy(() => import("@modules/app-infraccion/layout/ConsultaInfraccionLayout"));
const EncargadoInfraccionLayout = lazy(() => import("@modules/app-infraccion/layout/EncargadoInfraccionLayout"));
const InfraccionLogLayout = lazy(() => import("@modules/app-infraccion/layout/InfraccionLogLayout"));
const AsignarInformes = lazy(() => import("@modules/app-infraccion/layout/AsignarInformes"));
const MisInformes = lazy(() => import("@modules/app-infraccion/layout/MisInformes"));
const AlertasInfraccionLayout = lazy(() => import("@modules/app-infraccion/layout/AlertasInfraccionLayout"));
// === app-involved ===
const InvolucradoLogLayout = lazy(() => import("@modules/app-involved/layout/InvolucradoLogLayout"));
const ManageInvolvedLayout = lazy(() => import("@modules/app-involved/layout/ManageInvolvedLayout"));
// === app-documentos ===
const DocumentPage = lazy(() => import("@modules/app-documentos/layout/DocumentosPage"));

/**
 * Mientras baja el chunk de login/recover. Las pantallas privadas tienen su
 * propio Suspense alrededor del <Outlet/> de MainLayout (el Header no se va).
 */
const PageFallback = () => (
  <div className="fixed top-0 left-0 right-0 z-50">
    <LoadingBar />
  </div>
);

type ToastState = { id: number; message: string; type: "success" | "error" } | null;
type SetToast = React.Dispatch<React.SetStateAction<ToastState>>;
/** Pantalla enrutada: recibe `setToast` (las que no lo usan simplemente lo ignoran). */
type RoutedPage = React.ComponentType<{ setToast: SetToast }>;

type RouteConfig = {
  path: string;
  component: RoutedPage;
  props?: Record<string, unknown>;
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
  component: RoutedPage;
  path: string;
  props?: Record<string, unknown>;
  setToast: SetToast;
}) => {
  const permission = inferPermissionFromPath(path);

  return (
    <RequirePermission required={permission}>
      <Component setToast={setToast} {...props} />
    </RequirePermission>
  );
};

function App() {
  // Tema reactivo desde ThemeProvider (app/providers): persiste en localStorage.
  const { theme } = useTheme();
  const [toast, setToast] = useState<ToastState>(null);
  
  // Registrar el handler global permite lanzar toasts sin prop drilling.
  useEffect(() => {
    toastService.setHandler(setToast);
  }, []);


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
          <Suspense fallback={<PageFallback />}>
            <Routes>
              {/* páginas públicas */}
              <Route path="/login" element={<LoginPage theme={theme} />} />
              <Route path="/recover" element={<RecoverPage theme={theme} />} />

              {/* páginas privadas */}
              <Route
                path=""
                element={<MainLayout setToast={setToast} />}
              >
                {/* página de inicio (sin restricciones) */}
                <Route index element={<WelcomeLayout />} />

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
          </Suspense>
        </BrowserRouter>
      </ErrorBoundary>
    </div>
  );
}

export default App;
