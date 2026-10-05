import ConfirmacionModal from "../comun/ConfirmacionModal";
import { ICONOS } from "../comun/iconos";

type Props = {
  isOpen: boolean;
  isDeleting: boolean;
  onClose: () => void;
  onConfirm: () => void;
};

/** Confirma borrar el acto de etapa de la decisión (arrastra el acto de recurso). */
export default function DeleteStageModal({ isOpen, isDeleting, onClose, onConfirm }: Props) {
  return (
    <ConfirmacionModal
      isOpen={isOpen}
      onClose={onClose}
      onConfirm={onConfirm}
      titulo="Confirmar Eliminación"
      claseTitulo="text-error"
      tono="error"
      textoConfirmar="Eliminar Ambos"
      iconoConfirmar={ICONOS.papelera}
      procesando={isDeleting}
      textoProcesando="Eliminando..."
    >
      <p className="text-base-content/80 text-sm leading-relaxed">
        ¿Está seguro que desea eliminar el acto administrativo de etapa?
        <span className="block mt-3 font-medium text-tono-warning text-sm">
          ⚠️ Esto también eliminará el acto administrativo de recurso asociado.
        </span>
      </p>
    </ConfirmacionModal>
  );
}
