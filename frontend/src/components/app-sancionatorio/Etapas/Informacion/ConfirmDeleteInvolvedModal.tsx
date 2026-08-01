import { createPortal } from "react-dom";
import { useEffect, useState } from "react";

type Props = {
  user: { nombre: string; tipo_documento: string; numero_documento: number };
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

export default function ConfirmDeleteInvolvedModal({
  user,
  isOpen,
  onClose,
  onConfirm,
}: Props) {
  if (!isOpen) return null;
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

  return createPortal(
    <div className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm" data-theme={theme}>
      <div className="card bg-base-100 shadow-2xl w-full max-w-md mx-4 border border-base-300">
        <div className="card-body">
          {/* Header con ícono de alerta */}
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
                ¿Estás seguro de desvincular a{" "}
                <span className="font-semibold">{user.nombre}</span>{" "}
                {user.tipo_documento}: {user.numero_documento} del expediente?
              </p>
              <p className="text-base-content/70 text-sm mt-2">
                Esta acción eliminará la vinculación pero no eliminará los datos
                del involucrado del sistema.
              </p>

              {/* Alerta de advertencia */}
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
                  Esto también eliminará todas las notificaciones asociadas.
                </span>
              </div>
            </div>
          </div>

          {/* Divider */}
          <div className="divider my-2"></div>

          {/* Acciones */}
          <div className="card-actions justify-end">
            <button onClick={onClose} className="btn btn-ghost">
              Cancelar
            </button>
            <button
              onClick={() => {
                onConfirm();
                onClose();
              }}
              className="btn btn-error gap-2"
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
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                />
              </svg>
              Eliminar
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  );
}
