import { apiCall, API_CONFIG } from "../utils/api";
import { useState } from "react";
import MailInput from "../components/Input/MailInput";
import PasswordInput from "../components/Input/PasswordInput";

type Props = {
  theme: "emerald" | "dark";
};

export default function LoginPage({ theme }: Props) {
  const [mail, setMail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [remember, setRemember] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg("");
    try {
      const email = mail;
      const res = await apiCall(API_CONFIG.ENDPOINTS.AUTH_LOGIN, {
        method: "POST",
        body: JSON.stringify({ email, password, remember }),
      });

      if (res.ok) {
        window.location.href = "/";
      } else {
        const detail = res.detail;
        if (typeof detail === "string") {
          setErrorMsg(detail);
        } else if (Array.isArray(detail)) {
          setErrorMsg(
            detail.map((d: { msg?: string }) => d.msg).join(", ") ||
              "Error al iniciar sesión.",
          );
        } else {
          setErrorMsg("Error al iniciar sesión. Inténtalo de nuevo.");
        }
      }
    } catch (error) {
      /* console.error("Error al hacer fetch:", error); */
      setErrorMsg("No se pudo conectar al servidor.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-base-200 select-none" data-theme={theme}>
      <section className="w-full min-h-[calc(100vh)] flex items-center justify-center overflow-hidden">
        <div className="bg-base-100 rounded-3xl shadow-xl flex w-full max-w-5xl overflow-hidden border border-base-300">
          <div className="w-full md:w-1/2 p-10">
            <div className="mb-6 text-center">
              <h2 className="text-3xl font-bold mb-2">Iniciar sesión</h2>
              <p className="text-sm text-base-content/60">
                Ingresa tus credenciales para continuar
              </p>
            </div>
            <form onSubmit={handleSubmit} className="space-y-6">
              <MailInput
                title="Correo electrónico"
                value={mail}
                onChange={setMail}
              />
              <PasswordInput
                title="Contraseña"
                placeHolder="Contraseña"
                value={password}
                onChange={setPassword}
              />
              <div className="flex items-center justify-between text-sm">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="recordar"
                    className="checkbox checkbox-success checkbox-white-check"
                    onChange={(e) => setRemember(e.target.checked)}
                  />
                  Recuérdame
                </label>
                <a href="/recover" className="link link-success link-hover">
                  ¿Olvidaste tu contraseña?
                </a>
              </div>

              <button
                type="submit"
                className="btn btn-success w-full !text-white"
                disabled={isLoading}
              >
                {isLoading ? "Iniciando sesión..." : "Iniciar Sesión"}
              </button>
              {errorMsg && (
                <p className="text-error text-sm text-center mt-2">
                  {errorMsg}
                </p>
              )}
            </form>
          </div>
          <div
            className="hidden md:block md:w-1/2 bg-cover bg-center"
            style={{ backgroundImage: `url(/static/login-bg.jpg)` }}
            role="img"
          />
        </div>
      </section>
    </div>
  );
}
