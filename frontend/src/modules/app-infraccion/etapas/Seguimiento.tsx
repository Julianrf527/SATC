import InformeTecnicoEtapa from "../informe-tecnico/InformeTecnicoEtapa";

const STAGE_NAME = "Seguimiento";

type Props = {
  expedienteId: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
  onStageUpdate: (stage: string) => void;
  isEditable?: boolean;
};

/** Etapa "Visita Seguimiento": informe técnico SEGUIMIENTO. */
export default function Seguimiento({ expedienteId, setToast, onStageUpdate, isEditable }: Props) {
  return (
    <InformeTecnicoEtapa
      expedienteId={expedienteId}
      tipo="SEGUIMIENTO"
      etapa={STAGE_NAME}
      titulo={`Datos del ${STAGE_NAME}`}
      setToast={setToast}
      onStageUpdate={onStageUpdate}
      isEditable={isEditable}
    />
  );
}
