import { Modal } from "@shared/ui";
import type { TipoCambio, TipoOperacion } from "../types";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  typeOperation: TipoOperacion;
  typeChange?: TipoCambio;
  itemIdentifier?: string | number;
  isSubmitting?: boolean;
  warningMessage?: string;
};

const TITULO: Record<TipoOperacion, string> = {
  eliminar: "Eliminación",
  actualizar: "Actualización",
  crear: "Creación",
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
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel={`Confirmar ${TITULO[typeOperation]}`}
      showCloseButton={false}
      closeOnBackdrop={false}
      closeOnEsc={!isSubmitting}
      footer={
        <>
          <button onClick={onClose} className="btn btn-ghost" disabled={isSubmitting}>
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
        </>
      }
    >
      <div className="flex items-start gap-4 mb-2">
        <div className="w-12 h-12 bg-error/10 rounded-full flex items-center justify-center flex-shrink-0">
          <svg className="w-6 h-6 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        </div>
        <div className="flex-1">
          <h3 className="font-bold text-lg text-error mb-2">Confirmar {TITULO[typeOperation]}</h3>
          <p className="text-base-content/80 text-sm leading-relaxed">
            ¿Está seguro que desea {typeOperation} el {typeChange}{" "}
            <span className="font-semibold font-mono">{itemIdentifier}</span>?
          </p>
        </div>
      </div>

      {/* Advertencia adicional (ej: eliminar permiso de roles) */}
      {warningMessage && (
        <div className="flex items-start gap-2 bg-warning/10 border border-warning/30 rounded-lg p-3 mb-2">
          <svg className="w-4 h-4 text-warning flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-tono-warning text-xs leading-relaxed">{warningMessage}</p>
        </div>
      )}
    </Modal>
  );
}
