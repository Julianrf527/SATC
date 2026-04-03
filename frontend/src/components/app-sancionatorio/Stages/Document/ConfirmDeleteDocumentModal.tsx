import { useState, useEffect } from "react";
import { createPortal } from "react-dom";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  type: "documento" | "acto";
};

export default function ConfirmDeleteDocumentModal({
  isOpen,
  onClose,
  onConfirm,
  type,
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

  const titles = {
    documento: "¿Eliminar Documento?",
    acto: "¿Eliminar Acto Administrativo?",
  };

  const descriptions = {
    documento:
      "Esta acción eliminará permanentemente el documento. Esta acción no se puede deshacer.",
    acto: "Esta acción eliminará permanentemente el acto administrativo y toda su información asociada. Esta acción no se puede deshacer.",
  };

  const modalContent = (
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-base-100 rounded-lg p-6 w-full max-w-md mx-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start gap-4 mb-4">
          <div className="flex-shrink-0 w-12 h-12 bg-error/10 rounded-full flex items-center justify-center">
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
            <h3 className="font-bold text-lg text-base-content mb-2">
              {titles[type]}
            </h3>
            <p className="text-sm text-base-content/70">{descriptions[type]}</p>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button onClick={onClose} className="btn btn-ghost">
            Cancelar
          </button>
          <button onClick={onConfirm} className="btn btn-error text-white">
            Eliminar
          </button>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
