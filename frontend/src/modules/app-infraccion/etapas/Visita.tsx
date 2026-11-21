import InformeTecnicoEtapa from "../informe-tecnico/InformeTecnicoEtapa";
import type { InformeTecnico } from "../types";
import MatrizRecursosAfectadosView from "./MatrizRecursosAfectadosView";

const STAGE_NAME = "Visita Técnica";

type Props = {
  expedienteId: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
  isEditable?: boolean;
};

/**
 * Etapa "Visita Técnica": informe técnico VISITA + matriz de recursos afectados.
 * La matriz se diligencia al aceptar el informe (versión final del técnico) o
 * en el cargue directo de super gestión; aquí solo se consulta.
 */
export default function VisitStage({ expedienteId, setToast, isEditable }: Props) {
  const seccionMatriz = (informe: InformeTecnico) =>
    informe.aceptado && informe.tiene_matriz && informe.recursos_afectados ? (
      <MatrizRecursosAfectadosView filas={informe.recursos_afectados} />
    ) : null;

  return (
    <InformeTecnicoEtapa
      expedienteId={expedienteId}
      tipo="VISITA"
      codigoEtapa="visita"
      etapa={STAGE_NAME}
      titulo="Datos de la Visita Técnica"
      setToast={setToast}
      isEditable={isEditable}
      extra={seccionMatriz}
    />
  );
}
