import { createPortal } from "react-dom";
import { useEffect, useState } from "react";

type Props = {
  userName: string;
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export default function ConfirmResendPasswordModal({
  userName,
  isOpen,
  onClose,
  onConfirm,
}: Props) {
  const [theme, setTheme] = useState<string>("emerald");

  useEffect(() => {
    const updateTheme = () => {
      const currentTheme =
        document.querySelector("[data-theme]")?.getAttribute("data-theme") ||
        "emerald";
      setTheme(currentTheme);
    };

    updateTheme();

    const observer = new MutationObserver(updateTheme);
    const targetNode = document.querySelector("[data-theme]");

    if (targetNode) {
      observer.observe(targetNode, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    }

    return () => observer.disconnect();
  }, []);

  if (!isOpen) return null;

  return createPortal(
    <div className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm" data-theme={theme}>
      <div className="card bg-base-100 shadow-2xl w-full max-w-md mx-4 border border-base-300">
        <div className="card-body">
          <div className="flex items-start gap-4 mb-4">
            <div className="w-12 h-12 bg-warning/10 rounded-full flex items-center justify-center flex-shrink-0">
              <svg
                className="w-6 h-6 text-warning"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="font-bold text-lg text-warning mb-2">
                Reenviar Contraseña
              </h3>
              <p className="text-base-content/80 text-sm leading-relaxed">
                ¿Enviar una nueva contraseña temporal a{" "}
                <span className="font-semibold">{userName}</span>?
              </p>

              <div className="alert alert-warning mt-3 py-2 px-3">
                <svg
                  className="w-5 h-5 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
                <span className="text-xs">
                  Esto invalidará su sesión activa y su contraseña actual.
                </span>
              </div>
            </div>
          </div>

          <div className="divider my-2"></div>

          <div className="card-actions justify-end">
            <button onClick={onClose} className="btn btn-ghost">
              Cancelar
            </button>
            <button
              onClick={() => {
                onConfirm();
                onClose();
              }}
              className="btn btn-warning text-white gap-2"
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
              Reenviar
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
