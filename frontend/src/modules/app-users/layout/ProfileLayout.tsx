import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import TitleForm from "@shared/ui/label/TitleForm";
import type { PerfilUsuario, SetToast } from "../types";
import { logout, usePerfilQuery } from "../api/profile";
import PersonalDataForm from "../profile/PersonalDataForm";
import PasswordChangeForm from "../profile/PasswordChangeForm";

type Props = {
  setToast: SetToast;
};

const PERFIL_VACIO: PerfilUsuario = {
  primer_nombre: "",
  segundo_nombre: "",
  primer_apellido: "",
  segundo_apellido: "",
  correo: "",
};

export default function ProfileLayout({ setToast }: Props) {
  const navigate = useNavigate();
  const { data: perfil, isPending: isLoading, error } = usePerfilQuery();

  useEffect(() => {
    if (!error) return;
    setToast({ id: Date.now(), message: "Error al cargar los datos del usuario", type: "error" });
  }, [error, setToast]);

  /** Tras guardar: 2 s para leer el toast, cerrar sesión y volver al login. */
  const logoutDespuesDeGuardar = () => {
    setTimeout(async () => {
      await logout();
      navigate("/login");
    }, 2000);
  };

  if (isLoading) {
    return (
      <div className="bg-base-200 min-h-screen flex items-center justify-center">
        <span className="loading loading-spinner loading-lg"></span>
      </div>
    );
  }

  return (
    <div className="bg-base-200">
      <section className="w-full min-h-[calc(100vh-4rem)] flex items-center justify-center overflow-hidden p-4">
        <div className="w-full max-w-6xl">
          <div className="card bg-base-100 shadow-xl border border-base-300">
            <div className="card-body px-6 py-6">
              <div className="mb-6">
                <TitleForm
                  title="Mi Perfil"
                  body="Gestiona tu información personal y configuración de seguridad. Al actualizar, deberás iniciar sesión nuevamente."
                />
              </div>

              <div className="flex w-full flex-col lg:flex-row gap-6">
                {/* Sección de Datos Personales */}
                <PersonalDataForm
                  perfil={perfil ?? PERFIL_VACIO}
                  setToast={setToast}
                  onSaved={logoutDespuesDeGuardar}
                />

                {/* Divider */}
                <div className="divider lg:divider-horizontal"></div>

                {/* Sección de Seguridad */}
                <PasswordChangeForm setToast={setToast} onSaved={logoutDespuesDeGuardar} />
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
