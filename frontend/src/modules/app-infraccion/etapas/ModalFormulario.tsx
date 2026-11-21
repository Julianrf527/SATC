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
  /** "xl" por defecto; "2xl" para formularios largos (cargue directo del informe). */
  size?: ModalSize;
  children: ReactNode;
};

const FORM_ID = "form-etapa-infraccion";

/** Formulario en modal (réplica de `ModalFormulario` de recurso): Cancelar / Guardar y error abajo. */
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
          <button type="submit" form={FORM_ID} className="btn btn-success btn-sm text-white" disabled={ocupado}>
            {ocupado && <span className="loading loading-spinner loading-xs" />}
            {textoGuardar}
          </button>
        </>
      }
    >
      <form id={FORM_ID} onSubmit={enviar} className="space-y-4">
        {/* min-w-0: un <fieldset> se estira al ancho de su contenido (p. ej. la
            matriz) y desborda el modal con scroll horizontal. */}
        <fieldset disabled={ocupado} className="space-y-4 min-w-0">
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
