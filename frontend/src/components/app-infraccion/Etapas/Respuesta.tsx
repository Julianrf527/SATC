import { useEffect, useState, useCallback, useRef } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import { openDocumentById } from "../../../utils/documentViewer";
import RespuestaData from "./Respuesta/RespuestaData";
import MedidaPreventivaData from "./Respuesta/MedidaPreventivaData";

type RespuestaData = {
  id: number;
  expediente_id: number;
  radicado: string;
  fecha_radicado: string;
  documento_radicado_id: number;
  requiere_medida_preventiva: boolean;
  fecha_creacion: string;
};

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
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [showLoading, setShowLoading] = useState(false);
  const [respuestaData, setRespuestaData] = useState<RespuestaData | null>(null);
  const [medidaLocal, setMedidaLocal] = useState<any>(null);
  const [isCreatingStage, setIsCreatingStage] = useState(false);
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchAnswerData = useCallback(async () => {
    if (!expedienteId) {
      setIsLoadingData(false);
      return;
    }
    try {
      setIsLoadingData(true);
      loadingTimerRef.current = setTimeout(() => {
        setShowLoading(true);
      }, 300);

      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_GET_ANSWER(expedienteId),
        { method: "GET" },
      );

      if (res.status === 404) {
        // Normal: la etapa aún no existe
        setRespuestaData(null);
        setMedidaLocal(null);
        return;
      }

      if (res.ok) {
        setRespuestaData(res.respuesta_data);
        setMedidaLocal(res.medida_preventiva?.ok ? res.medida_preventiva.medida : null);
      } else {
        // Error real del servidor (no 404)
        setToast({
          id: Date.now(),
          message: "Error al cargar la etapa respuesta",
          type: "error",
        });
      }
    } catch (error) {
      if (import.meta.env.DEV) console.error("Error fetching answer data:", error);
      setToast({
        id: Date.now(),
        message: "Error de conexión al cargar la respuesta",
        type: "error",
      });
    } finally {
      setIsLoadingData(false);
      setShowLoading(false);
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
    }
  }, [expedienteId]);

  useEffect(() => {
    fetchAnswerData();
  }, [expedienteId]);

  // Callback que se llama desde RespuestaData tras guardar exitosamente
  const handleSaveSuccess = useCallback(async () => {
    setIsCreatingStage(false);
    // Re-consultar BD para confirmar que el dato existe antes de mostrarlo
    await fetchAnswerData();
    onStageUpdate(STAGE_NAME);
  }, [fetchAnswerData, onStageUpdate]);

  const handleViewDocument = (fileId: number) => {
    openDocumentById(fileId);
  };

  if (isLoadingData && showLoading) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <span className="loading loading-spinner loading-lg text-primary"></span>
            <p className="text-gray-600 font-medium">Cargando datos...</p>
            <p className="text-sm text-gray-500">
              Obteniendo información de la etapa respuesta. Esto puede tardar unos segundos.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!expedienteId) {
    return (
      <div className="card bg-base-100 shadow w-full">
        <div className="card-body flex items-center justify-center text-gray-500">
          <p>
            Seleccione un expediente para ver {isEditable ? "o editar" : ""} sus datos
          </p>
        </div>
      </div>
    );
  }

  if (isLoadingData) {
    return <div className="min-h-[200px]" />;
  }

  if (!respuestaData?.id && !isEditable) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-gray-400 to-gray-500 rounded-full p-4 shadow-lg">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-16 w-16 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <div className="text-center space-y-3">
              <p className="text-gray-600 max-w-md mx-auto">
                Este expediente aún no tiene la etapa de{" "}
                <span className="font-semibold text-gray-700 whitespace-nowrap">
                  "{STAGE_NAME}"
                </span>
                .
              </p>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                No hay información disponible para visualizar en esta etapa.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!respuestaData?.id && !isCreatingStage) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-blue-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-full p-4 shadow-lg">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-16 w-16 text-white"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <div className="text-center space-y-3">
              <p className="text-gray-600 max-w-md mx-auto">
                Este expediente aún no tiene la etapa de{" "}
                <span className="font-semibold text-blue-400 whitespace-nowrap">
                  "{STAGE_NAME}"
                </span>
                .
              </p>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                Para continuar, debe crear esta etapa y así poder gestionar la etapa
                respuesta correspondiente.
              </p>
            </div>
            <button
              className="btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
              onClick={() => setIsCreatingStage(true)}
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z"
                  clipRule="evenodd"
                />
              </svg>
              Crear Etapa
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {(respuestaData || isCreatingStage) && (
        <RespuestaData
          expedienteId={expedienteId}
          handleViewDocument={handleViewDocument}
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
          localMedida={medidaLocal}
          isEditable={isEditable}
          setToast={setToast}
          handleViewFile={handleViewDocument}
          onMedidaUpdated={fetchAnswerData}
        />
      )}
    </div>
  );
}
