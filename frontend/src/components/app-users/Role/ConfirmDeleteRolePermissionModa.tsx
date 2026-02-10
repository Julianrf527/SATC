import { createPortal } from "react-dom";
import { useEffect, useState } from "react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  type: "rol" | "permiso";
  itemName?: string;
  isDeleting?: boolean;
};

export default function ConfirmDeleteRolePermissionModal({
  isOpen,
  onClose,
  onConfirm,
  type,
  itemName,
  isDeleting = false,
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

  const getTypeText = () => {
    return type === "rol" ? "rol" : "permiso";
  };

  const getQuestionText = () => {
    const typeText = getTypeText();

    if (itemName) {
      return (
        <>
          ¿Está seguro que desea eliminar {type === "rol" ? "el" : "el"}{" "}
          {typeText}{" "}
          <span className="font-semibold text-error">"{itemName}"</span>?
        </>
      );
    }

    return `¿Está seguro que desea eliminar este ${typeText}?`;
  };

  const getWarningText = () => {
    if (type === "rol") {
      return (
        <span className="block mt-3 font-medium text-warning text-sm">
          ⚠️ Esto afectará a todos los usuarios que tengan este rol asignado.
        </span>
      );
    }

    if (type === "permiso") {
      return (
        <span className="block mt-3 font-medium text-warning text-sm">
          ⚠️ Asegúrate de que este permiso no esté asignado a ningún rol antes
          de eliminarlo.
        </span>
      );
    }

    return null;
  };

  const getIcon = () => {
    if (type === "rol") {
      return (
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
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
      );
    }

    return (
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
          d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
        />
      </svg>
    );
  };

  return createPortal(
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
    >
      <div className="card bg-base-100 shadow-2xl w-full max-w-md mx-4">
        <div className="card-body">
          <div className="flex items-start gap-4 mb-4">
            <div className="w-12 h-12 bg-error/10 rounded-full flex items-center justify-center flex-shrink-0">
              {getIcon()}
            </div>
            <div className="flex-1">
              <h3 className="font-bold text-lg text-error mb-2">
                Confirmar Eliminación
              </h3>
              <p className="text-base-content/80 text-sm leading-relaxed">
                {getQuestionText()}
                {getWarningText()}
              </p>
            </div>
          </div>

          <div className="divider my-2"></div>

          <div className="card-actions justify-end">
            <button
              onClick={onClose}
              className="btn btn-ghost"
              disabled={isDeleting}
            >
              Cancelar
            </button>
            <button
              onClick={onConfirm}
              className="btn btn-error text-white gap-2"
              disabled={isDeleting}
            >
              {isDeleting ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Eliminando...
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
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                    />
                  </svg>
                  Eliminar
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
