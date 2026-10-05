import type { FormEvent, ReactNode, RefObject } from "react";
import { AlertCircle, Check, Plus } from "lucide-react";

type Props = {
  formId: string;
  formRef: RefObject<HTMLFormElement | null>;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
  onCancelar: () => void;
  isSubmitting: boolean;
  /** Mensaje del bloque de error general al final del formulario (null = oculto). */
  errorGeneral?: string | null;
  /** Campos del formulario (cada módulo compone los suyos). */
  children: ReactNode;
  /** Contenido fuera del <form> (p. ej. modales auxiliares). */
  extra?: ReactNode;
};

/**
 * Armazón del formulario "Nuevo Expediente" de la lista lateral: cabecera,
 * cuerpo con scroll y botones fijos Cancelar / Agregar.
 */
export default function NuevoExpedienteLayout({
  formId,
  formRef,
  onSubmit,
  onCancelar,
  isSubmitting,
  errorGeneral,
  children,
  extra,
}: Props) {
  return (
    <div className="flex flex-col h-full bg-base-100">
      <div className="flex-shrink-0 p-6 border-b border-base-300">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
            <Plus className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-base-content">Nuevo Expediente</h2>
            <p className="text-sm text-base-content/60">Completa la información del expediente</p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6">
        <form ref={formRef} onSubmit={onSubmit} id={formId} className="space-y-4">
          {children}

          {errorGeneral && (
            <div className="alert alert-error shadow-sm">
              <AlertCircle className="w-5 h-5" />
              <span>{errorGeneral}</span>
            </div>
          )}
        </form>
      </div>

      <div className="flex-shrink-0 p-6 border-t border-base-300 bg-base-100">
        <div className="flex gap-3 justify-end">
          <button
            type="button"
            className="btn btn-outline"
            onClick={onCancelar}
            disabled={isSubmitting}
          >
            Cancelar
          </button>
          <button
            type="submit"
            form={formId}
            className="btn btn-success text-white"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="loading loading-spinner loading-sm"></span>
                Guardando...
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                Agregar Expediente
              </>
            )}
          </button>
        </div>
      </div>

      {extra}
    </div>
  );
}
