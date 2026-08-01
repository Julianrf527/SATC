import React, { useEffect, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import { useNavigate } from "react-router-dom";
import TitleForm from "../../Common/Label/TitleForm";
import Input from "../../Common/Input/Input";
import MailInput from "../../Common/Input/MailInput";
import PasswordInput from "../../Common/Input/PasswordInput";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function ProfileLayout({ setToast }: Props) {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [isSavingData, setIsSavingData] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);

  const [firstName, setFirstName] = useState("");
  const [middleName, setMiddleName] = useState("");
  const [lastName, setLastName] = useState("");
  const [secondLastName, setSecondLastName] = useState("");
  const [email, setEmail] = useState("");

  // Estados originales para restaurar
  const [firstNameOriginal, setFirstNameOriginal] = useState("");
  const [middleNameOriginal, setMiddleNameOriginal] = useState("");
  const [lastNameOriginal, setLastNameOriginal] = useState("");
  const [secondLastNameOriginal, setSecondLastNameOriginal] = useState("");
  const [emailOriginal, setEmailOriginal] = useState("");

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");

  useEffect(() => {
    const fetchUserData = async () => {
      try {
        const res = await apiCall(API_CONFIG.ENDPOINTS.AUTH_ME, {
          method: "GET",
        });

        if (res.ok && res.usuario) {
          const primerNombre = res.usuario.primer_nombre || "";
          const segundoNombre = res.usuario.segundo_nombre || "";
          const primerApellido = res.usuario.primer_apellido || "";
          const segundoApellido = res.usuario.segundo_apellido || "";
          const correo = res.usuario.correo || "";

          setFirstName(primerNombre);
          setMiddleName(segundoNombre);
          setLastName(primerApellido);
          setSecondLastName(segundoApellido);
          setEmail(correo);

          setFirstNameOriginal(primerNombre);
          setMiddleNameOriginal(segundoNombre);
          setLastNameOriginal(primerApellido);
          setSecondLastNameOriginal(segundoApellido);
          setEmailOriginal(correo);
        } else {
          setToast({
            id: Date.now(),
            message: "Error al cargar los datos del usuario",
            type: "error",
          });
        }
      } catch (error) {
        setToast({
          id: Date.now(),
          message: "Error al cargar los datos del usuario",
          type: "error",
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchUserData();
  }, []);

  const capitalize = (text: string): string => {
    return (
      text.trim().charAt(0).toUpperCase() + text.trim().slice(1).toLowerCase()
    );
  };

  const handleLogout = async () => {
    try {
      await apiCall(API_CONFIG.ENDPOINTS.AUTH_LOGOUT, {
        method: "POST",
      });
    } catch (error) {
    } finally {
      // Redirigir al login independientemente del resultado
      navigate("/login");
    }
  };

  const handleUpdateData = async (e: React.FormEvent) => {
    e.preventDefault();

    if (isSavingData) return;

    if (!firstName.trim()) {
      setToast({
        id: Date.now(),
        message: "El primer nombre es obligatorio",
        type: "error",
      });
      return;
    }

    if (!lastName.trim()) {
      setToast({
        id: Date.now(),
        message: "El primer apellido es obligatorio",
        type: "error",
      });
      return;
    }

    setIsSavingData(true);

    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.USER_UPDATE, {
        method: "PUT",
        body: JSON.stringify({
          first_name: capitalize(firstName),
          middle_name: middleName.trim() ? capitalize(middleName) : "",
          lastname: capitalize(lastName),
          second_lastname: secondLastName.trim()
            ? capitalize(secondLastName)
            : "",
          correo: email.toLowerCase(),
        }),
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Datos actualizados. Cerrando sesión...",
          type: "success",
        });

        // Esperar 2 segundos para que se vea el mensaje y luego hacer logout
        setTimeout(() => {
          handleLogout();
        }, 2000);
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al actualizar datos",
          type: "error",
        });
        setIsSavingData(false);
      }
    } catch (error) {
      setToast({
        id: Date.now(),
        message: "Error de conexión al actualizar datos",
        type: "error",
      });
      setIsSavingData(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();

    if (isSavingPassword) return;

    setPasswordError("");

    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError("Todos los campos son obligatorios");
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError("La contraseña debe tener al menos 8 caracteres");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("Las contraseñas no coinciden");
      return;
    }

    setIsSavingPassword(true);

    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.PASSWORD_CHANGE, {
        method: "POST",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Contraseña actualizada. Cerrando sesión...",
          type: "success",
        });

        // Esperar 2 segundos para que se vea el mensaje y luego hacer logout
        setTimeout(() => {
          handleLogout();
        }, 2000);
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al cambiar contraseña",
          type: "error",
        });
        setIsSavingPassword(false);
      }
    } catch (error) {
      setToast({
        id: Date.now(),
        message: "Error de conexión al cambiar contraseña",
        type: "error",
      });
      setIsSavingPassword(false);
    }
  };

  const handleRestoreData = () => {
    setFirstName(firstNameOriginal);
    setMiddleName(middleNameOriginal);
    setLastName(lastNameOriginal);
    setSecondLastName(secondLastNameOriginal);
    setEmail(emailOriginal);
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
                <div className="flex-1 flex flex-col">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-info/10 rounded-lg flex items-center justify-center">
                      <svg
                        className="w-5 h-5 text-info"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                        />
                      </svg>
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg">
                        Datos Personales
                      </h3>
                      <p className="text-sm text-base-content/60">
                        Actualiza tu información personal
                      </p>
                    </div>
                  </div>

                  <form
                    className="flex flex-col flex-1"
                    onSubmit={handleUpdateData}
                  >
                    <div className="flex-1 space-y-4">
                      {/* Nombres */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Input
                          title="Primer nombre *"
                          placeholder="Primer nombre"
                          type="text"
                          required={true}
                          maxLength={20}
                          value={firstName}
                          onChange={(e) => setFirstName(e.target.value)}
                        />
                        <Input
                          title="Segundo nombre"
                          placeholder="Segundo nombre (opcional)"
                          type="text"
                          required={false}
                          maxLength={20}
                          value={middleName}
                          onChange={(e) => setMiddleName(e.target.value)}
                        />
                      </div>

                      {/* Apellidos */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <Input
                          title="Primer apellido *"
                          placeholder="Primer apellido"
                          type="text"
                          required={true}
                          maxLength={20}
                          value={lastName}
                          onChange={(e) => setLastName(e.target.value)}
                        />
                        <Input
                          title="Segundo apellido"
                          placeholder="Segundo apellido (opcional)"
                          type="text"
                          required={false}
                          maxLength={20}
                          value={secondLastName}
                          onChange={(e) => setSecondLastName(e.target.value)}
                        />
                      </div>

                      {/* Email */}
                      <MailInput
                        title="Correo electrónico *"
                        value={email}
                        onChange={setEmail}
                      />
                    </div>

                    {/* Botones - Pegados al final */}
                    <div className="pt-6 space-y-2 mt-auto">
                      <button
                        type="submit"
                        className="btn btn-info text-white w-full gap-2"
                        disabled={isSavingData}
                      >
                        {isSavingData ? (
                          <>
                            <span className="loading loading-spinner loading-sm"></span>
                            Guardando...
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
                                d="M5 13l4 4L19 7"
                              />
                            </svg>
                            Guardar Cambios
                          </>
                        )}
                      </button>

                      <button
                        type="button"
                        className="btn btn-ghost w-full gap-2"
                        onClick={handleRestoreData}
                        disabled={isSavingData}
                      >
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
                            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                          />
                        </svg>
                        Restaurar
                      </button>
                    </div>
                  </form>
                </div>

                {/* Divider */}
                <div className="divider lg:divider-horizontal"></div>

                {/* Sección de Seguridad */}
                <div className="flex-1 flex flex-col">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-warning/10 rounded-lg flex items-center justify-center">
                      <svg
                        className="w-5 h-5 text-warning"
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
                      <h3 className="font-semibold text-lg">Seguridad</h3>
                      <p className="text-sm text-base-content/60">
                        Cambia tu contraseña
                      </p>
                    </div>
                  </div>

                  <form
                    className="flex flex-col flex-1"
                    onSubmit={handleChangePassword}
                  >
                    <div className="flex-1 space-y-4">
                      <PasswordInput
                        title="Contraseña actual"
                        placeHolder="Ingresa tu contraseña actual"
                        value={currentPassword}
                        onChange={setCurrentPassword}
                      />

                      <PasswordInput
                        title="Nueva contraseña"
                        placeHolder="Mínimo 8 caracteres"
                        value={newPassword}
                        onChange={setNewPassword}
                      />

                      <PasswordInput
                        title="Confirmar contraseña"
                        placeHolder="Confirma tu contraseña"
                        value={confirmPassword}
                        onChange={setConfirmPassword}
                      />

                      {passwordError && (
                        <div className="alert alert-error py-2">
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
                              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                            />
                          </svg>
                          <span className="text-sm">{passwordError}</span>
                        </div>
                      )}
                    </div>

                    {/* Botones - Pegados al final a la misma altura que el otro formulario */}
                    <div className="pt-6 space-y-2 mt-auto">
                      <button
                        type="submit"
                        className="btn btn-warning text-white w-full gap-2"
                        disabled={isSavingPassword}
                      >
                        {isSavingPassword ? (
                          <>
                            <span className="loading loading-spinner loading-sm"></span>
                            Actualizando...
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
                                d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                              />
                            </svg>
                            Cambiar Contraseña
                          </>
                        )}
                      </button>

                      <button
                        type="button"
                        className="btn btn-ghost w-full gap-2"
                        onClick={() => {
                          setCurrentPassword("");
                          setNewPassword("");
                          setConfirmPassword("");
                          setPasswordError("");
                        }}
                        disabled={isSavingPassword}
                      >
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
                        Limpiar
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
