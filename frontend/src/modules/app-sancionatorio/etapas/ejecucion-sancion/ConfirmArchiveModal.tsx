import ConfirmacionModal from "../comun/ConfirmacionModal";
import Icono from "../comun/Icono";
import { ICONOS } from "../comun/iconos";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  radicado: string;
  isArchiving?: boolean;
};

export default function ConfirmArchiveModal({
  isOpen,
  onClose,
  onConfirm,
  radicado,
  isArchiving = false,
}: Props) {
  return (
    <ConfirmacionModal
      isOpen={isOpen}
      onClose={onClose}
      onConfirm={onConfirm}
      titulo="Confirmar Archivado"
      claseTitulo="text-tono-warning"
      icono={ICONOS.archivar}
      tono="warning"
      textoConfirmar="Archivar Expediente"
      iconoConfirmar={ICONOS.archivar}
      procesando={isArchiving}
      textoProcesando="Archivando..."
    >
      <p className="text-base-content/80 text-sm leading-relaxed">
        ¿Está seguro que desea archivar el expediente{" "}
        <span className="font-semibold font-mono">{radicado}</span>?
      </p>
      <div className="bg-warning/10 border border-warning/30 rounded-lg p-3 mt-3">
        <p className="text-sm font-medium text-tono-warning flex items-start gap-2">
          <Icono d={ICONOS.alerta} className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <span>
            Esta acción no se puede deshacer. El expediente archivado no
            aparecerá en la vista de gestión pero seguirá visible en la
            consulta general.
          </span>
        </p>
      </div>
    </ConfirmacionModal>
  );
}
