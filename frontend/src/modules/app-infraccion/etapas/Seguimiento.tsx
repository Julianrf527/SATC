import InformeTecnicoEtapa from "../informe-tecnico/InformeTecnicoEtapa";

const STAGE_NAME = "Seguimiento";

type Props = {
  expedienteId: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
  isEditable?: boolean;
};

/** Etapa "Visita Seguimiento": informe técnico SEGUIMIENTO. */
export default function Seguimiento({ expedienteId, setToast, isEditable }: Props) {
  return (
    <InformeTecnicoEtapa
      expedienteId={expedienteId}
      tipo="SEGUIMIENTO"
      etapa={STAGE_NAME}
      titulo={`Datos del ${STAGE_NAME}`}
      setToast={setToast}
      isEditable={isEditable}
    />
  );
}
