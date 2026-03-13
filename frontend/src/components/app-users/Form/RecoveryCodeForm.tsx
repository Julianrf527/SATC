import { useRef, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";

type Props = {
  email?: string;
  setToast: (toast: { message: string; type: "success" | "error" }) => void;
};

export default function CodeForm({ email, setToast }: Props) {
  const [valid, setValid] = useState(false);
  const [code, setCode] = useState<string[]>(Array(5).fill(""));
  const [isLoading, setIsLoading] = useState(false);
  const inputsRef = useRef<Array<HTMLInputElement | null>>([]);

  const handleChange = (value: string, index: number) => {
    if (!/^[a-zA-Z0-9]?$/.test(value)) return;
    const newCode = [...code];
    newCode[index] = value.toUpperCase();
    setCode(newCode);

    if (value && index < code.length - 1) {
      inputsRef.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (
    e: React.KeyboardEvent<HTMLInputElement>,
    index: number
  ) => {
    if (e.key === "Backspace" && !code[index] && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pasteData = e.clipboardData.getData("text").slice(0, code.length);
    const newCode = pasteData.split("").map((c) => c.toUpperCase());

    setCode(newCode);

    newCode.forEach((c, i) => {
      if (inputsRef.current[i]) {
        inputsRef.current[i]!.value = c;
      }
    });
    inputsRef.current[Math.min(newCode.length - 1, code.length - 1)]?.focus();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Si ya es válido, redirigir al login
    if (valid) {
      window.location.href = "/login";
      return;
    }

    // Prevenir múltiples envíos
    if (isLoading) return;

    setIsLoading(true);
    const finalCode = code.join("");

    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.AUTH_RECOVERY_CODE, {
        method: "POST",
        body: JSON.stringify({ email, code: finalCode }),
      });

      if (res.ok) {
        setToast({
          message: "Recibiste una contraseña temporal en tu correo",
          type: "success",
        });
        setValid(true);
      } else {
        setToast({ message: "Código inválido o expirado", type: "error" });
      }
    } catch (error) {
      /* console.error("Error al hacer fetch:", error); */
      setToast({
        message: "Error de conexión, intenta más tarde",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 text-center">
      <div className="flex justify-center gap-2">
        {code.map((digit, index) => (
          <input
            key={index}
            type="text"
            inputMode="text"
            maxLength={1}
            value={digit}
            disabled={isLoading || valid}
            ref={(el) => {
              inputsRef.current[index] = el;
            }}
            onChange={(e) => handleChange(e.target.value, index)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            onPaste={handlePaste}
            className="w-12 h-12 text-center border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 uppercase disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
        ))}
      </div>

      <button
        type="submit"
        className="btn btn-success text-white w-full"
        disabled={isLoading}
      >
        {isLoading ? "Verificando..." : valid ? "Volver al Login" : "Enviar"}
      </button>
    </form>
  );
}
