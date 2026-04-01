import { useEffect, useState, useCallback, useRef } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import DataStageExecution from "./Execution/DataStageExecution";
import ConfirmArchiveModal from "./Execution/ConfirmArchiveModal";

type Execution = {
  id?: number;
  cobro_coactivo: boolean;
  cobro_coactivo_doc_url: string | null;
  disposicion: boolean;
  ruia: boolean;
  ruia_doc_url: string | null;
  memorando: boolean;
  memorando_doc_url: string | null;
  auto_admin: string;
  fecha_auto: string | null;
  auto_doc_url: string | null;
  etapa_id: number;
  tipo_etapa_id?: number;
  creable?: { status: boolean; msg?: string };
};

type Props = {
  radicado: string;
  idAuxiliar: number;
  onStageUpdate: (stage: string) => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
  onArchiveSuccess?: () => void;
};

const STAGE_NAME = "EJECUCION DE LA SANCION";

export default function ExecutionOfSanction({
  radicado,
  idAuxiliar,
  onStageUpdate,
  setToast,
  isEditable = true,
  onArchiveSuccess,
}: Props) {
  const [isCreatingStage, setIsCreatingStage] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [showLoading, setShowLoading] = useState(false);
  const [localExecution, setLocalExecution] = useState<any>(null);
  const [executionData, setExecutionData] = useState<Execution | undefined>();
  const [etapaId, setEtapaId] = useState<number | null>(null);
  const [showArchiveModal, setShowArchiveModal] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const loadingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const fetchExecution = useCallback(async () => {
    if (!radicado) {
      setIsLoadingData(false);
      return;
    }

    try {
      setIsLoadingData(true);

      loadingTimerRef.current = setTimeout(() => {
        setShowLoading(true);
      }, 300);

      const res = await apiCall(API_CONFIG.ENDPOINTS.FILE_EXECUTION(radicado), {
        method: "GET",
      });

      if (res.ok) {
        // Extraer etapa_id del response principal
        const etapaIdFromResponse = res.etapa_id;

        // Los datos pueden venir en ejecucion_sancion directamente
        const execData = res.ejecucion_sancion;

        setLocalExecution(execData);
        setEtapaId(etapaIdFromResponse || execData?.etapa_id || null);

        // Si tiene id, significa que hay datos guardados
        if (execData && execData.id) {
          setExecutionData(execData);
        } else {
          setExecutionData(undefined);
        }
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al cargar ejecución de la sanción.",
          type: "error",
        });
      }
    } catch (e) {
      /* console.error("Error fetching execution:", e); */
      setToast({
        id: Date.now(),
        message: "Error al cargar ejecución de la sanción.",
        type: "error",
      });
    } finally {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
      setShowLoading(false);
      setIsLoadingData(false);
    }
  }, [radicado, setToast]);

  useEffect(() => {
    fetchExecution();
    return () => {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
    };
  }, [fetchExecution]);

  const stageExists = etapaId !== null;
  const tipoEtapaId = localExecution?.tipo_etapa_id || null;
  const creable = localExecution?.creable || { status: true, msg: "" };

  const createStage = async () => {
    if (!radicado) {
      setToast({
        id: Date.now(),
        message: "No se ha seleccionado un expediente.",
        type: "error",
      });
      return;
    }

    if (!tipoEtapaId) {
      setToast({
        id: Date.now(),
        message: "No se pudo obtener el tipo de etapa.",
        type: "error",
      });
      return;
    }

    try {
      setIsCreatingStage(true);

      const res = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_CREATE_STAGE(radicado, tipoEtapaId),
        { method: "POST" },
      );

      if (res.ok && res.etapa_id) {
        setEtapaId(res.etapa_id);
        setExecutionData(undefined);
        onStageUpdate(STAGE_NAME);

        setToast({
          id: Date.now(),
          message: "Etapa creada exitosamente.",
          type: "success",
        });
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al crear la etapa.",
          type: "error",
        });
      }
    } catch (e) {
      /* console.error("Error creando etapa:", e); */
      setToast({
        id: Date.now(),
        message: "Error al crear la etapa.",
        type: "error",
      });
    } finally {
      setIsCreatingStage(false);
    }
  };

  const handleExecutionUpdate = useCallback(() => {
    fetchExecution();
  }, [fetchExecution]);

  const handleArchiveClick = () => {
    setShowArchiveModal(true);
  };

  const handleArchiveConfirm = async () => {
    if (!radicado) return;

    try {
      setIsArchiving(true);

      const res = await apiCall(API_CONFIG.ENDPOINTS.FILE_ARCHIVE(radicado), {
        method: "PATCH",
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Expediente archivado exitosamente.",
          type: "success",
        });

        setShowArchiveModal(false);

        // Notificar cambio al componente padre
        onStageUpdate(STAGE_NAME);

        // Deseleccionar y eliminar de la lista
        if (onArchiveSuccess) {
          onArchiveSuccess();
        }
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al archivar el expediente.",
          type: "error",
        });
      }
    } catch (e) {
      /* console.error("Error archivando expediente:", e); */
      setToast({
        id: Date.now(),
        message: "Error al archivar el expediente.",
        type: "error",
      });
    } finally {
      setIsArchiving(false);
    }
  };

  if (isLoadingData && showLoading) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <span className="loading loading-spinner loading-lg text-primary"></span>
            <p className="text-gray-600 font-medium">Cargando datos...</p>
            <p className="text-sm text-gray-500">
              Obteniendo información de ejecución de la sanción
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!radicado) {
    return (
      <div className="card bg-base-100 shadow w-full">
        <div className="card-body flex items-center justify-center text-gray-500">
          <p>
            Seleccione un expediente para ver {isEditable ? "o editar" : ""} sus
            datos
          </p>
        </div>
      </div>
    );
  }

  if (isLoadingData) {
    return <div className="min-h-[200px]" />;
  }

  if (!creable.status && isEditable) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-warning/30">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-warning to-orange-500 rounded-full p-4 shadow-lg">
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
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
            </div>

            <div className="text-center space-y-3">
              <h3 className="text-lg font-semibold">
                No es posible gestionar o crear esta etapa
              </h3>
              <div className="bg-warning/10 border border-amber-200 rounded-lg p-4 max-w-lg mx-auto">
                <p className="text-sm font-medium">
                  <span className="font-semibold text-warning">Motivo:</span>{" "}
                  {creable.msg}
                </p>
              </div>
              <p className="text-sm opacity-70 max-w-md mx-auto mt-4">
                Por favor, complete los requisitos necesarios antes de crear
                esta etapa.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!stageExists && !isEditable) {
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
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
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

  if (!stageExists && creable.status) {
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
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
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
                Para continuar, debe crear esta etapa y así poder gestionar la
                información de ejecución de la sanción.
              </p>
            </div>

            <button
              className="btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
              onClick={createStage}
              disabled={isCreatingStage}
            >
              {isCreatingStage ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Creando etapa...
                </>
              ) : (
                <>
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
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (stageExists && etapaId) {
    return (
      <div className="space-y-6">
        <DataStageExecution
          data={executionData as any} // TODO: Arreglar tipos después de migración completa
          idAuxiliar={idAuxiliar}
          setToast={setToast}
          etapaId={etapaId}
          tipoEtapa="ejecucion_sancion"
          onDataUpdated={handleExecutionUpdate}
          isEditable={isEditable}
        />

        {/* Botón de Archivar - Solo si hay datos guardados y es editable */}
        {executionData?.id && isEditable && (
          <div className="card bg-gradient-to-br from-warning/5 to-orange-50 shadow-lg border border-warning/20">
            <div className="card-body">
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-warning/20 rounded-full flex items-center justify-center flex-shrink-0">
                    <svg
                      className="w-6 h-6 text-warning"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                      />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-bold text-lg mb-1">
                      Archivar Expediente
                    </h3>
                    <p className="text-sm text-base-content/70">
                      Una vez completada la ejecución de la sanción, puede
                      archivar este expediente. Los expedientes archivados no
                      aparecerán en la gestión pero seguirán disponibles para
                      consulta.
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleArchiveClick}
                  className="btn btn-warning text-white gap-2 shadow-md hover:shadow-lg transition-all whitespace-nowrap"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"
                    />
                  </svg>
                  Archivar Expediente
                </button>
              </div>
            </div>
          </div>
        )}

        <ConfirmArchiveModal
          isOpen={showArchiveModal}
          onClose={() => setShowArchiveModal(false)}
          onConfirm={handleArchiveConfirm}
          radicado={radicado}
          isArchiving={isArchiving}
        />
      </div>
    );
  }

  return null;
}
