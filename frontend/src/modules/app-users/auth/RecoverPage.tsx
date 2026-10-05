import { useState } from "react";
import RecoveryEmailForm from "../form/RecoveryEmailForm";
import RecoveryCodeForm from "../form/RecoveryCodeForm";
import Toast from "@shared/ui/Toast";

type Props = {
  theme: "emerald" | "dark";
};

function RecoverPage({ theme }: Props) {
  const [activeForm, setActiveForm] = useState<"email" | "code">("email");
  const [email, setEmail] = useState("");
  const [toast, setToast] = useState<{
    message: string;
    type: "success" | "error";
  } | null>(null);

  const bodyText =
    activeForm === "code"
      ? "Revisa tu correo e ingresa el código"
      : "Ingresa tus credenciales para continuar";

  return (
    <div className="bg-base-200 select-none" data-theme={theme}>
      <section className="w-full min-h-[calc(100vh)] flex items-center justify-center overflow-hidden">
        <div className="bg-base-100 rounded-3xl shadow-xl flex w-full max-w-lg overflow-hidden border border-base-300">
          <div className="w-full p-10">
            <div className="mb-6 text-center">
              <h2 className="text-3xl font-bold mb-2">
                Recuperacion de contraseña
              </h2>
              <p className="text-sm text-base-content/60">{bodyText}</p>
            </div>
            {activeForm === "email" && (
              <RecoveryEmailForm
                setActiveForm={setActiveForm}
                setEmail={setEmail}
                setToast={setToast}
              />
            )}
            {activeForm === "code" && (
              <RecoveryCodeForm email={email} setToast={setToast} />
            )}
          </div>
        </div>
        {toast && (
          <Toast
            message={toast.message}
            type={toast.type}
            id={Date.now()}
            duration={4000}
          />
        )}
      </section>
    </div>
  );
}

export default RecoverPage;
