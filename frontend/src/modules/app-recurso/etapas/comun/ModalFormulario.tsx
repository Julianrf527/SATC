import type { FormEvent, ReactNode } from "react";
import { AlertCircle } from "lucide-react";
import { Modal, type ModalSize } from "@shared/ui";

type Props = {
  titulo: string;
  subtitulo?: ReactNode;
  icono: ReactNode;
  ocupado: boolean;
  error: string | null;
  textoGuardar: string;
  onGuardar: () => void;
  onClose: () => void;
  size?: ModalSize;
  children: ReactNode;
};

/** Formulario de etapa en modal (como los de infraction): Cancelar / Guardar y error abajo. */
export default function ModalFormulario({
  titulo,
  subtitulo,
  icono,
  ocupado,
  error,
  textoGuardar,
  onGuardar,
  onClose,
  size = "xl",
  children,
}: Props) {
  const enviar = (e: FormEvent) => {
    e.preventDefault();
    onGuardar();
  };
  return (
    <Modal
      isOpen
      onClose={onClose}
      size={size}
      icon={icono}
      title={titulo}
      subtitle={subtitulo}
      closeOnEsc={!ocupado}
      closeOnBackdrop={!ocupado}
      footer={
        <>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onClose} disabled={ocupado}>
            Cancelar
          </button>
          <button type="submit" form="form-etapa-recurso" className="btn btn-success btn-sm text-white" disabled={ocupado}>
            {ocupado && <span className="loading loading-spinner loading-xs" />}
            {textoGuardar}
          </button>
        </>
      }
    >
      <form id="form-etapa-recurso" onSubmit={enviar} className="space-y-4">
        <fieldset disabled={ocupado} className="space-y-4">
          {children}
        </fieldset>
        {error && (
          <div role="alert" className="alert alert-error py-2 text-sm">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
      </form>
    </Modal>
  );
}
