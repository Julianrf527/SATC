import ConfirmacionModal from "../comun/ConfirmacionModal";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  type: "documento" | "acto";
};

const TITULOS = {
  documento: "¿Eliminar Documento?",
  acto: "¿Eliminar Acto Administrativo?",
};

const DESCRIPCIONES = {
  documento:
    "Esta acción eliminará permanentemente el documento. Esta acción no se puede deshacer.",
  acto: "Esta acción eliminará permanentemente el acto administrativo y toda su información asociada. Esta acción no se puede deshacer.",
};

export default function ConfirmDeleteDocumentModal({ isOpen, onClose, onConfirm, type }: Props) {
  return (
    <ConfirmacionModal
      isOpen={isOpen}
      onClose={onClose}
      onConfirm={onConfirm}
      titulo={TITULOS[type]}
      tono="error"
      textoConfirmar="Eliminar"
      cerrarConFondo
    >
      <p className="text-sm text-base-content/70">{DESCRIPCIONES[type]}</p>
    </ConfirmacionModal>
  );
}
