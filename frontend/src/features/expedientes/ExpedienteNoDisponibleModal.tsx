import type { ReactNode } from "react";
import { AlertTriangle, ChevronRight } from "lucide-react";
import { Modal } from "@shared/ui";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  titulo?: string;
  subtitulo?: string;
  /** Cuerpo del aviso; por defecto, el texto de desvinculación del expediente. */
  children?: ReactNode;
};

/**
 * Aviso cuando se navega a un expediente (notificación, alerta, informe) que
 * no está en la lista del usuario. Los textos se pueden sustituir por props.
 */
export default function ExpedienteNoDisponibleModal({
  isOpen,
  onClose,
  titulo = "Acceso Denegado",
  subtitulo = "No tienes permisos para este expediente",
  children,
}: Props) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={titulo}
      subtitle={subtitulo}
      icon={<AlertTriangle size={22} className="text-tono-warning" />}
      size="md"
      footer={
        <button type="button" onClick={onClose} className="btn btn-success text-white gap-2">
          <ChevronRight size={16} />
          Entendido
        </button>
      }
    >
      {children ?? (
        <>
          <p className="text-sm text-base-content/80 leading-relaxed">
            Ya no te encuentras vinculado con este expediente. Es posible que hayas sido
            desvinculado o que el expediente haya sido reasignado a otro usuario.
          </p>
          <div className="mt-4 p-4 bg-info/10 rounded-lg border border-info/20">
            <p className="text-xs text-base-content/70">
              <strong>Nota:</strong> Si crees que esto es un error, contacta al administrador del
              sistema.
            </p>
          </div>
        </>
      )}
    </Modal>
  );
}
