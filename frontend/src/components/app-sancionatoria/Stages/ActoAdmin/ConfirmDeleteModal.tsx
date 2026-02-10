import { createPortal } from "react-dom";
import { useEffect, useState } from "react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  type: "tipo" | "notificacion" | "acto" | "comunicacion" | "documento";
  itemIdentifier?: string | number;
  isDeleting?: boolean;
  tipoActo?: "notificacion" | "comunicacion";
  deleteWarning?: string; // Warning personalizado
};

export default function ConfirmDeleteModal({
  isOpen,
  onClose,
  onConfirm,
  type,
  itemIdentifier,
  isDeleting = false,
  tipoActo,
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

  const formatIdentifier = (identifier: string | number | undefined) => {
    if (!identifier) return "";
    const str = String(identifier);
    if (/^\d{1,4}$/.test(str)) {
      return str.padStart(4, "0");
    }
    return str;
  };

  const getTypeText = () => {
    switch (type) {
      case "tipo":
        return "tipo de notificación";
      case "notificacion":
        return "notificación";
      case "acto":
        return "acto administrativo";
      case "comunicacion":
        return "comunicación";
      default:
        return "elemento";
    }
  };

  const getQuestionText = () => {
    const typeText = getTypeText();

    if (itemIdentifier) {
      const formattedId = formatIdentifier(itemIdentifier);

      switch (type) {
        case "comunicacion":
          return (
            <>
              ¿Está seguro que desea eliminar la {typeText}{" "}
              <span className="font-semibold font-mono">{formattedId}</span>?
            </>
          );
        case "acto":
          return (
            <>
              ¿Está seguro que desea eliminar el {typeText}{" "}
              <span className="font-semibold font-mono">{formattedId}</span>?
            </>
          );
        default:
          return `¿Está seguro que desea eliminar esta ${typeText}?`;
      }
    }

    return `¿Está seguro que desea eliminar este ${typeText}?`;
  };

  const getWarningText = () => {
    if (type === "tipo") {
      return (
        <span className="block mt-3 font-medium text-warning text-sm">
          ⚠️ Esto también eliminará todas las notificaciones asociadas.
        </span>
      );
    }

    if (type === "acto") {
      if (tipoActo === "comunicacion") {
        return (
          <span className="block mt-3 font-medium text-warning text-sm">
            ⚠️ Esto también eliminará la comunicación asociada si existe.
          </span>
        );
      }

      if (tipoActo === "notificacion") {
        return (
          <span className="block mt-3 font-medium text-warning text-sm">
            ⚠️ Esto también eliminará todas las notificaciones asociadas.
          </span>
        );
      }
    }

    if (type === "comunicacion") {
      return (
        <span className="block mt-3 font-medium text-warning text-sm">
          ⚠️ Esta acción no se puede deshacer. El documento asociado también
          será eliminado.
        </span>
      );
    }

    if (type === "notificacion") {
      return (
        <span className="block mt-3 font-medium text-warning text-sm">
          ⚠️ Esta acción no se puede deshacer.
        </span>
      );
    }

    return null;
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
