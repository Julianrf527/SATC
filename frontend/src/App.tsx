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
import FileManageLayout from "./components/app-sancionatoria/Layout/FileManageLayout";
import FileViewLayout from "./components/app-sancionatoria/Layout/FileViewLayout";
import ManagerFilesLayout from "./components/app-sancionatoria/Layout/ManagerFilesLayout";
import AlertsLayout from "./components/app-sancionatoria/Layout/AlertsLayout";
import FileLogLayout from "./components/app-sancionatoria/Layout/FileLogLayout";
import ManageInvolvedLayout from "./components/app-sancionatoria/Layout/ManageInvolvedLayout";
import DocumentPage from "./components/app-documentos/layout/DocumentosPage";

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
          {/* públicas */}
          <Route path="/login" element={<LoginPage theme={theme} />} />
          <Route path="/recover" element={<RecoverPage theme={theme} />} />

          {/* privadas */}
          <Route
            path="/"
            element={<MainLayout setTheme={setTheme} setToast={setToast} />}
          >
            <Route index element={<WelcomeLayout theme={theme} />} />

            <Route
              path="profile"
              element={<ProfileLayout setToast={setToast} />}
            />

            <Route
              path="user/log"
              element={
                <RequirePermission required="admin_auditoria usuarios">
                  <UserLogLayout setToast={setToast} />
                </RequirePermission>
              }
            />

            <Route
              path="file/log"
              element={
                <RequirePermission required="admin_auditoria expedientes">
                  <FileLogLayout setToast={setToast} />
                </RequirePermission>
              }
            />

            <Route
              path="user/add"
              element={
                <RequirePermission required="admin_registrar usuario">
                  <SignUpLayout setToast={setToast} />
                </RequirePermission>
              }
            />

            <Route
              path="user/manage"
              element={
                <RequirePermission required="admin_gestionar usuarios">
                  <ManageUserLayout setToast={setToast} />
                </RequirePermission>
              }
            />

            <Route
              path="user/role"
              element={
                <RequirePermission required="admin_roles y permisos">
                  <RoleLayout setToast={setToast} />
                </RequirePermission>
              }
            />
            <Route
              path="file/manage"
              element={
                <RequirePermission required="expediente_gestionar">
                  <FileManageLayout setToast={setToast} />
                </RequirePermission>
              }
            />
            <Route
              path="file/consult"
              element={
                <RequirePermission required="expediente_consular">
                  <FileViewLayout setToast={setToast} />
                </RequirePermission>
              }
            />
            <Route
              path="file/alerts"
              element={
                <RequirePermission required="expediente_alertas">
                  <AlertsLayout setToast={setToast} />
                </RequirePermission>
              }
            />
            <Route
              path="file/assign_manage"
              element={
                <RequirePermission required="expediente_asignar encargados">
                  <ManagerFilesLayout setToast={setToast} />
                </RequirePermission>
              }
            />
            <Route
              path="file/involved/manage"
              element={
                <RequirePermission required="expediente_gestionar involucrados">
                  <ManageInvolvedLayout setToast={setToast} />
                </RequirePermission>
              }
            />
            <Route
              path="document/manage"
              element={
                <RequirePermission required="documento_gestionar">
                  <DocumentPage setToast={setToast} />
                </RequirePermission>
              }
            />
          </Route>
          {/* cualquier ruta desconocida fuera de "/" redirige a main */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
