import { useState } from "react";
import { apiCall, API_CONFIG } from "@shared/lib/api";
import MailInput from "@shared/ui/input/MailInput";

type Props = {
  setActiveForm: (form: "email" | "code") => void;
  setEmail: (email: string) => void;
  setToast: (toast: { message: string; type: "success" | "error" }) => void;
};

export default function EmailForm({
  setActiveForm,
  setEmail,
  setToast,
}: Props) {
  const [mail, setMail] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Prevenir múltiples envíos
    if (isLoading) return;

    setIsLoading(true);

    const email = mail;

    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.AUTH_RECOVERY, {
        method: "POST",
        body: JSON.stringify({ email }),
      });

      if (res.ok) {
        setActiveForm("code");
        setEmail(email!);
        setToast({
          message: res.message || "Codigo validado",
          type: "success",
        });
      } else {
        setToast({ message: res.detail || "Error inesperado", type: "error" });
      }
    } catch {
      setToast({
        message: "Error de conexión, intenta más tarde",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <MailInput title="Correo electrónico" value={mail} onChange={setMail} />
      <button
        type="submit"
        className="btn btn-success text-white w-full"
        disabled={isLoading}
      >
        {isLoading ? "Enviando..." : "Enviar"}
      </button>
    </form>
  );
}
