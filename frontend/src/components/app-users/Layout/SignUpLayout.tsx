import React, { useRef, useState } from "react";
import { UserPlus, KeyRound } from "lucide-react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import Input from "../../Common/Input/Input";
import RolList from "../Role/RolList";

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

export default function SignUpLayout({ setToast }: Props) {
  const firstNameRef = useRef<HTMLInputElement>(null);
  const middleNameRef = useRef<HTMLInputElement>(null);
  const lastNameRef = useRef<HTMLInputElement>(null);
  const secondLastNameRef = useRef<HTMLInputElement>(null);
  const documentRef = useRef<HTMLInputElement>(null);
  const emailRef = useRef<HTMLInputElement>(null);
  const rolRef = useRef<HTMLSelectElement>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);

  const cleanInputs = () => {
    if (firstNameRef.current) firstNameRef.current.value = "";
    if (middleNameRef.current) middleNameRef.current.value = "";
    if (lastNameRef.current) lastNameRef.current.value = "";
    if (secondLastNameRef.current) secondLastNameRef.current.value = "";
    if (documentRef.current) documentRef.current.value = "";
    if (emailRef.current) emailRef.current.value = "";
    if (rolRef.current) rolRef.current.value = "0";
  };

  const capitalize = (text: string): string =>
    text.trim().charAt(0).toUpperCase() + text.trim().slice(1).toLowerCase();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const document = documentRef.current!.value;
    if (document.length < 6) {
      setToast({
        id: Date.now(),
        message: "El documento debe tener al menos 6 dígitos",
        type: "error",
      });
      documentRef.current?.focus();
      return;
    }
    const rolValue = rolRef.current!.value;
    if (!rolValue || rolValue === "0") {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar un rol",
        type: "error",
      });
      return;
    }
    setIsSubmitting(true);
    try {
      const first_name = capitalize(firstNameRef.current!.value);
      const middle_name = middleNameRef.current?.value.trim()
        ? capitalize(middleNameRef.current.value)
        : "";
      const lastname = capitalize(lastNameRef.current!.value);
      const second_lastname = secondLastNameRef.current?.value.trim()
        ? capitalize(secondLastNameRef.current.value)
        : "";
      const email = emailRef.current!.value.trim().toLowerCase();
      const rol = parseInt(rolValue);

      const res = await apiCall(API_CONFIG.ENDPOINTS.USER_REGISTER, {
        method: "POST",
        body: JSON.stringify({
          first_name,
          middle_name,
          lastname,
          second_lastname,
          document: parseInt(document),
          email,
          rol,
        }),
      });

      if (res.ok) {
        cleanInputs();
        setToast({
          id: Date.now(),
          message:
            "Usuario registrado exitosamente. Se ha enviado la contraseña al correo.",
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al registrar usuario",
          type: "error",
        });
      }
    } catch {
      setToast({
        id: Date.now(),
        message: "Error de conexión al registrar usuario",
        type: "error",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
                <UserPlus className="text-success" size={20} />
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                  Módulo de Usuarios
                </p>
                <h1 className="text-lg font-bold text-base-content">
                  Registrar Usuario
                </h1>
              </div>
            </div>
            <div className="hidden sm:flex items-center gap-2">
              <KeyRound className="text-info/70 flex-shrink-0" size={14} />
              <p className="text-xs text-info/70 font-medium leading-tight max-w-[220px]">
                Se enviará contraseña temporal al correo. El usuario deberá
                cambiarla en su primer inicio de sesión.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-7xl mx-auto">
          <div className="card bg-base-100 shadow border border-base-300">
          <div className="card-body px-6 py-6">
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* Datos personales */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 bg-info/10 rounded-lg flex items-center justify-center flex-shrink-0">
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
                        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                      />
                    </svg>
                  </div>
                  <h2 className="font-semibold text-base-content">
                    Datos personales
                  </h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    title="Primer nombre *"
                    placeholder="Primer nombre"
                    type="text"
                    required
                    inputRef={firstNameRef}
                    maxLength={20}
                  />
                  <Input
                    title="Segundo nombre"
                    placeholder="Segundo nombre (opcional)"
                    type="text"
                    required={false}
                    inputRef={middleNameRef}
                    maxLength={20}
                  />
                  <Input
                    title="Primer apellido *"
                    placeholder="Primer apellido"
                    type="text"
                    required
                    inputRef={lastNameRef}
                    maxLength={20}
                  />
                  <Input
                    title="Segundo apellido"
                    placeholder="Segundo apellido (opcional)"
                    type="text"
                    required={false}
                    inputRef={secondLastNameRef}
                    maxLength={20}
                  />
                </div>
              </div>

              <div className="divider my-1" />

              {/* Contacto e identidad */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <svg
                      className="w-4 h-4 text-primary"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                      />
                    </svg>
                  </div>
                  <h2 className="font-semibold text-base-content">
                    Contacto e identidad
                  </h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Input
                    title="Número de documento *"
                    placeholder="Documento de identidad"
                    type="number"
                    required
                    inputRef={documentRef}
                    minLength={6}
                  />
                  <Input
                    title="Correo electrónico *"
                    placeholder="correo@ejemplo.com"
                    type="email"
                    required
                    inputRef={emailRef}
                  />
                </div>
              </div>

              <div className="divider my-1" />

              {/* Rol */}
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <div className="w-8 h-8 bg-success/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <svg
                      className="w-4 h-4 text-success"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                      />
                    </svg>
                  </div>
                  <h2 className="font-semibold text-base-content">Rol *</h2>
                </div>
                <RolList rolRef={rolRef} />
              </div>

              {/* Botones */}
              <div className="flex justify-end gap-3 pt-4 border-t border-base-300">
                <button
                  type="button"
                  className="btn btn-ghost gap-2"
                  onClick={cleanInputs}
                  disabled={isSubmitting}
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
                <button
                  type="submit"
                  className="btn bg-green-600 hover:bg-green-700 text-white border-0 gap-2"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? (
                    <>
                      <span className="loading loading-spinner loading-sm" />
                      Registrando...
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
                      Registrar Usuario
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
          </div>
        </div>
      </div>
    </>
  );
}
