import type { ReactNode } from "react";
import { Modal } from "@shared/ui";
import Icono from "./Icono";
import { ICONOS } from "./iconos";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  titulo: string;
  /** Clases del título (color). */
  claseTitulo?: string;
  /** Trazo del icono circular (por defecto alerta). */
  icono?: string;
  tono: "error" | "warning";
  /** Descripción / advertencias. */
  children: ReactNode;
  textoConfirmar: string;
  /** Icono del botón confirmar (opcional). */
  iconoConfirmar?: string;
  procesando?: boolean;
  textoProcesando?: string;
  /** Cerrar al hacer clic en el fondo (por defecto false). */
  cerrarConFondo?: boolean;
  /** Clases extra del botón confirmar. */
  claseConfirmar?: string;
};

const TONO = {
  error: { circulo: "bg-error/10", icono: "text-error", boton: "btn-error" },
  warning: { circulo: "bg-warning/10", icono: "text-tono-warning", boton: "btn-warning" },
} as const;

/** Diálogo de confirmación (icono + título + texto, Cancelar / Confirmar). */
export default function ConfirmacionModal({
  isOpen,
  onClose,
  onConfirm,
  titulo,
  claseTitulo = "text-base-content",
  icono = ICONOS.alerta,
  tono,
  children,
  textoConfirmar,
  iconoConfirmar,
  procesando = false,
  textoProcesando,
  cerrarConFondo = false,
  claseConfirmar = "text-white",
}: Props) {
  const t = TONO[tono];
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      ariaLabel={titulo}
      showCloseButton={false}
      closeOnBackdrop={cerrarConFondo && !procesando}
      closeOnEsc={!procesando}
      footer={
        <>
          <button onClick={onClose} className="btn btn-ghost" disabled={procesando}>
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            className={`btn ${t.boton} ${claseConfirmar} gap-2`}
            disabled={procesando}
          >
            {procesando ? (
              <>
                <span className="loading loading-spinner loading-sm"></span>
                {textoProcesando}
              </>
            ) : (
              <>
                {iconoConfirmar && <Icono d={iconoConfirmar} />}
                {textoConfirmar}
              </>
            )}
          </button>
        </>
      }
    >
      <div className="flex items-start gap-4 py-2">
        <div className={`w-12 h-12 ${t.circulo} rounded-full flex items-center justify-center flex-shrink-0`}>
          <Icono d={icono} className={`w-6 h-6 ${t.icono}`} />
        </div>
        <div className="flex-1">
          <h3 className={`font-bold text-lg mb-2 ${claseTitulo}`}>{titulo}</h3>
          {children}
        </div>
      </div>
    </Modal>
  );
}
