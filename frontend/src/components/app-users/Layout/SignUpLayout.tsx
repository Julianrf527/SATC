import React, { useRef, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import TitleForm from "../../Label/TitleForm";
import Input from "../../Input/Input";
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

  const [errorMsg, setErrorMsg] = useState("");
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

  const capitalize = (text: string): string => {
    return (
      text.trim().charAt(0).toUpperCase() + text.trim().slice(1).toLowerCase()
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg("");

    // Solo validar lo que HTML no puede validar
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
    if (rolValue === "0") {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar un rol",
        type: "error",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      // Capitalizar y limpiar espacios
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
    } catch (error) {
      console.error("Error al registrar:", error);
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
    <div className="bg-base-200">
      <section className="w-full min-h-[calc(100vh-4rem)] flex items-center justify-center overflow-hidden p-4">
        <div className="w-full max-w-4xl">
          <div className="card bg-base-100 shadow-xl border border-base-300 w-full">
            <div className="card-body px-6 py-6">
              <TitleForm
                title="Registrar Usuario"
                body="Complete la información del usuario. Los campos con * son obligatorios."
              />

              <form className="space-y-6 mt-4" onSubmit={handleSubmit}>
                {/* Datos personales */}
                <div>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 bg-info/10 rounded-lg flex items-center justify-center">
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
                    <h3 className="font-semibold text-lg">Datos personales</h3>
                  </div>

                  {/* Nombres */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Input
                      title="Primer nombre *"
                      placeholder="Primer nombre"
                      type="text"
                      required={true}
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
                  </div>

                  {/* Apellidos */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                    <Input
                      title="Primer apellido *"
                      placeholder="Primer apellido"
                      type="text"
                      required={true}
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

                  {/* Documento y Email */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
                    <Input
                      title="Número de documento *"
                      placeholder="Documento de identidad"
                      type="number"
                      required={true}
                      inputRef={documentRef}
                      minLength={6}
                    />
                    <Input
                      title="Correo electrónico *"
                      placeholder="correo@ejemplo.com"
                      type="email"
                      required={true}
                      inputRef={emailRef}
                    />
                  </div>

                  {/* Nota informativa */}
                  <div className="mt-4 bg-info/10 border border-info/20 rounded-lg p-3">
                    <div className="flex gap-2">
                      <svg
                        className="w-5 h-5 text-info flex-shrink-0 mt-0.5"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      <div className="text-sm text-info">
                        <p className="font-medium">Información importante:</p>
                        <p className="mt-1">
                          Se generará una contraseña temporal y se enviará al
                          correo electrónico proporcionado. El usuario deberá
                          cambiarla en su primer inicio de sesión.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Divider */}
                <div className="divider"></div>

                {/* Rol */}
                <div>
                  <div className="flex items-center gap-3 mb-4">
                    <div className="w-8 h-8 bg-success/10 rounded-lg flex items-center justify-center">
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
                    <h3 className="font-semibold text-lg">Rol y permisos *</h3>
                  </div>

                  <RolList rolRef={rolRef} setErrorMsg={setErrorMsg} />
                </div>

                {errorMsg && (
                  <div className="alert alert-error shadow-lg">
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
                        d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <span className="text-sm">{errorMsg}</span>
                  </div>
                )}

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
                    className="btn btn-success text-white gap-2"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? (
                      <>
                        <span className="loading loading-spinner loading-sm"></span>
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
                            d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
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
      </section>
    </div>
  );
}
