import { useCallback, useState } from "react";
import { useDelayedFlag } from "@shared/hooks/useDelayedFlag";
import { openDocumentById } from "@shared/lib/documentViewer";
import { useRespuestaEtapaQuery } from "../api/etapas";
import RespuestaData from "./respuesta/RespuestaData";
import MedidaPreventivaData from "./respuesta/MedidaPreventivaData";
import {
  EtapaCargando,
  EtapaHueco,
  EtapaNoExiste,
  EtapaPorCrear,
  EtapaSinExpediente,
  IconoMas,
} from "./EtapaEstados";
import { ICONOS_ETAPA } from "./iconosEtapa";
import { useAvisoErrorCarga } from "./useAvisoErrorCarga";

type Props = {
  expedienteId: number;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  onStageUpdate: (stage: string) => void;
  isEditable?: boolean;
};

const STAGE_NAME = "Respuesta";

export default function Respuesta({
  expedienteId,
  setToast,
  onStageUpdate,
  isEditable = true,
}: Props) {
  const [isCreatingStage, setIsCreatingStage] = useState(false);
  const query = useRespuestaEtapaQuery(expedienteId);
  const showLoading = useDelayedFlag(query.isPending && !!expedienteId, 300);

  useAvisoErrorCarga(query.error, setToast, {
    http: "Error al cargar la etapa respuesta",
    conexion: "Error de conexión al cargar la respuesta",
  });

  const respuestaData = query.data?.data?.respuesta ?? null;
  const medida = query.data?.data?.medida ?? null;

  // RespuestaData guarda con la mutación, que ya re-consultó la etapa.
  const handleSaveSuccess = useCallback(() => {
    setIsCreatingStage(false);
    onStageUpdate(STAGE_NAME);
  }, [onStageUpdate]);

  if (showLoading) return <EtapaCargando etapa="respuesta" />;
  if (!expedienteId) return <EtapaSinExpediente isEditable={isEditable} />;
  if (query.isPending) return <EtapaHueco />;

  if (!respuestaData?.id && !isEditable) return <EtapaNoExiste etapa={STAGE_NAME} />;

  if (!respuestaData?.id && !isCreatingStage) {
    return (
      <EtapaPorCrear
        etapa={STAGE_NAME}
        icono={ICONOS_ETAPA.escudo}
        descripcion="Para continuar, debe crear esta etapa y así poder gestionar la etapa respuesta correspondiente."
      >
        <button
          className="btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
          onClick={() => setIsCreatingStage(true)}
        >
          <IconoMas />
          Crear Etapa
        </button>
      </EtapaPorCrear>
    );
  }

  return (
    <div className="space-y-6">
      {(respuestaData || isCreatingStage) && (
        <RespuestaData
          expedienteId={expedienteId}
          handleViewDocument={openDocumentById}
          respuestaData={respuestaData}
          isCreatingStage={isCreatingStage}
          setIsCreatingStage={setIsCreatingStage}
          isEditable={isEditable}
          setToast={setToast}
          onSaveSuccess={handleSaveSuccess}
        />
      )}
      {respuestaData?.requiere_medida_preventiva && (
        <MedidaPreventivaData
          expedienteId={expedienteId}
          etapaRespuestaId={respuestaData.id}
          localMedida={medida}
          isEditable={isEditable}
          setToast={setToast}
        />
      )}
    </div>
  );
}
