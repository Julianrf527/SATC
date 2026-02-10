import { createPortal } from "react-dom";
import { useEffect, useState } from "react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  radicado: string;
  isArchiving?: boolean;
};

export default function ConfirmArchiveModal({
  isOpen,
  onClose,
  onConfirm,
  radicado,
  isArchiving = false,
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
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
    >
      <div className="card bg-base-100 shadow-2xl w-full max-w-md mx-4">
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
                  d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="font-bold text-lg text-warning mb-2">
                Confirmar Archivado
              </h3>
              <p className="text-base-content/80 text-sm leading-relaxed">
                ¿Está seguro que desea archivar el expediente{" "}
                <span className="font-semibold font-mono">{radicado}</span>?
              </p>
              <div className="bg-warning/10 border border-warning/30 rounded-lg p-3 mt-3">
                <p className="text-sm font-medium text-warning flex items-start gap-2">
                  <svg
                    className="w-5 h-5 flex-shrink-0 mt-0.5"
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
                  <span>
                    Esta acción no se puede deshacer. El expediente archivado no
                    aparecerá en la vista de gestión pero seguirá visible en la
                    consulta general.
                  </span>
                </p>
              </div>
            </div>
          </div>

          <div className="divider my-2"></div>

          <div className="card-actions justify-end">
            <button
              onClick={onClose}
              className="btn btn-ghost"
              disabled={isArchiving}
            >
              Cancelar
            </button>
            <button
              onClick={onConfirm}
              className="btn btn-warning text-white gap-2"
              disabled={isArchiving}
            >
              {isArchiving ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Archivando...
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
                      d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                    />
                  </svg>
                  Archivar Expediente
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
