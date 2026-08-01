import { createPortal } from "react-dom";
import { useEffect, useState } from "react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  typeOperation: "eliminar" | "actualizar" | "crear";
  typeChange?: "rol" | "permiso";
  itemIdentifier?: string | number;
  isSubmitting?: boolean;
  warningMessage?: string;
};

export default function ConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  typeOperation,
  typeChange,
  isSubmitting = false,
  itemIdentifier,
  warningMessage,
}: Props) {
  const [theme, setTheme] = useState<string>(() => {
    // Leer tema actual del DOM antes del primer render
    const appRoot = document.querySelector("#root > div[data-theme]");
    return (
      appRoot?.getAttribute("data-theme") ||
      localStorage.getItem("theme") ||
      "emerald"
    );
  });

  useEffect(() => {
    if (!isOpen) return;

    const updateTheme = () => {
      // Selector específico para el div de App, no el modal
      const appRoot = document.querySelector("#root > div[data-theme]");
      const currentTheme = appRoot?.getAttribute("data-theme") || "emerald";
      setTheme(currentTheme);
    };

    updateTheme();

    const handleThemeChange = (e: Event) => {
      const customEvent = e as CustomEvent<{ theme: string }>;
      setTheme(customEvent.detail.theme);
    };

    window.addEventListener("themeChange", handleThemeChange);

    // Observar cambios en el atributo data-theme del div de App (backup)
    const observer = new MutationObserver(updateTheme);
    const appRoot = document.querySelector("#root > div[data-theme]");

    if (appRoot) {
      observer.observe(appRoot, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    }

    return () => {
      observer.disconnect();
      window.removeEventListener("themeChange", handleThemeChange);
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return createPortal(
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
    >
      <div className="card bg-base-100 shadow-2xl w-full max-w-md mx-4">
        <div className="card-body">
          <div className="flex items-start gap-4 mb-4">
            <div className="w-12 h-12 bg-error/10 rounded-full flex items-center justify-center flex-shrink-0">
              <svg
                className="w-6 h-6 text-error"
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
              <h3 className="font-bold text-lg text-error mb-2">
                Confirmar{" "}
                {typeOperation === "eliminar"
                  ? "Eliminación"
                  : typeOperation === "actualizar"
                    ? "Actualización"
                    : "Creación"}
              </h3>
              <p className="text-base-content/80 text-sm leading-relaxed">
                <>
                  ¿Está seguro que desea {typeOperation} el {typeChange}{" "}
                  <span className="font-semibold font-mono">
                    {itemIdentifier}
                  </span>
                  ?
                </>
              </p>
            </div>
          </div>

          {/* Advertencia adicional (ej: eliminar permiso de roles) */}
          {warningMessage && (
            <div className="flex items-start gap-2 bg-warning/10 border border-warning/30 rounded-lg p-3 mb-2">
              <svg className="w-4 h-4 text-warning flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-warning text-xs leading-relaxed">{warningMessage}</p>
            </div>
          )}

          <div className="divider my-2"></div>

          <div className="card-actions justify-end">
            <button
              onClick={onClose}
              className="btn btn-ghost"
              disabled={isSubmitting}
            >
              Cancelar
            </button>
            <button
              onClick={onConfirm}
              className="btn btn-primary text-white gap-2"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Procesando...
                </>
              ) : (
                <>Aceptar</>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}
