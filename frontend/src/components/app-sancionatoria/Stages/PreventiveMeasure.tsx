import { useEffect, useState, useCallback, useRef } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import ActoAdmin from "./ActoAdmin/ActoAdmin";
import Documentos from "./Document/Document";
import DataStageMeasure from "./PreventiveMeasure/DataStageMeasure";

type DocumentoData = {
  id: number;
  nombre: string;
  url_documento: string;
  fecha_subida: string;
};

type Props = {
  radicado: string;
  idAuxiliar: number;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  onStageUpdate: (stage: string) => void;
  isEditable?: boolean;
};

const STAGE_NAME = "DETALLE MEDIDA PREVENTIVA";
const TIPOS_DOCUMENTO = ["Informe Tecnico", "Solicitud Revocatoria Directa"];

export default function PreventiveMeasure({
  radicado,
  idAuxiliar,
  setToast,
  onStageUpdate,
  isEditable = true,
}: Props) {
  const [isCreatingStage, setIsCreatingStage] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [showLoading, setShowLoading] = useState(false);
  const [localMedida, setLocalMedida] = useState<any>(null);
  const [existActoAdmin, setExistActoAdmin] = useState<boolean>(false);
  const [documentos, setDocumentos] = useState<DocumentoData[]>([]);
  const loadingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const fetchMedida = useCallback(async () => {
    if (!radicado) {
      setIsLoadingData(false);
      return;
    }

    try {
      setIsLoadingData(true);

      // Solo mostrar loading si tarda más de 300ms
      loadingTimerRef.current = setTimeout(() => {
        setShowLoading(true);
      }, 300);

      const res = await apiCall(API_CONFIG.ENDPOINTS.FILE_MEASURE(radicado), {
        method: "GET",
      });

      if (res.ok) {
        setLocalMedida(res.medida);
        setDocumentos(res.medida?.documento || []);
        if (res.medida?.acto_admin?.id) {
          setExistActoAdmin(true);
        }
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al obtener la medida preventiva.",
          type: "error",
        });
      }
    } catch (e) {
      /* console.error("Error fetching medida preventiva:", e); */
      setToast({
        id: Date.now(),
        message: "Error al obtener la medida preventiva.",
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
    fetchMedida();

    return () => {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
    };
  }, [fetchMedida]);

  const createStage = async () => {
    if (!radicado) {
      setToast({
        id: Date.now(),
        message: "No se ha seleccionado un expediente.",
        type: "error",
      });
      return;
    }

    if (!localMedida?.tipo_etapa_id) {
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
        API_CONFIG.ENDPOINTS.FILE_CREATE_STAGE(
          radicado,
          localMedida.tipo_etapa_id
        ),
        { method: "POST" }
      );

      if (res.ok && res.etapa_id) {
        const nuevaMedida = {
          etapa_id: res.etapa_id,
          informacion: {},
          acto_admin: {},
          documento: [],
          tipo_etapa_id: localMedida.tipo_etapa_id,
        };
        setLocalMedida(nuevaMedida);
        setDocumentos([]);
        setExistActoAdmin(false);
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

  const handleDocumentosUpdate = useCallback(
    (updatedDocumentos: DocumentoData[]) => {
      setDocumentos(updatedDocumentos);
    },
    []
  );

  // Solo mostrar loading si está cargando Y ha pasado el delay
  if (isLoadingData && showLoading) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <span className="loading loading-spinner loading-lg text-primary"></span>
            <p className="text-gray-600 font-medium">Cargando datos...</p>
            <p className="text-sm text-gray-500">
              Obteniendo información de la medida preventiva
            </p>
          </div>
        </div>
      </div>
    );
  }

  // No File Selected
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

  // Si aún está cargando pero no ha pasado el delay, mostrar contenedor vacío
  if (isLoadingData) {
    return <div className="min-h-[200px]" />;
  }

  // Stage Doesn't Exist - Read Only
  if (!localMedida?.etapa_id && !isEditable) {
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

  // Stage Doesn't Exist - Editable
  if (!localMedida?.etapa_id) {
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
                Para continuar, debe crear esta etapa y así poder gestionar la
                medida preventiva correspondiente.
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

  // Stage Exists - Show Content
  return (
    <div className="space-y-6">
      <ActoAdmin
        radicado={radicado}
        idAuxiliar={idAuxiliar}
        actoAdmin={localMedida.acto_admin || {}}
        etapaId={localMedida.etapa_id}
        tipoEtapa="detalle_medida_preventiva"
        tipoActo="comunicacion"
        setToast={setToast}
        isEditable={isEditable}
        setExistActoAdmin={setExistActoAdmin}
      />
      {existActoAdmin && (
        <DataStageMeasure
          data={localMedida.informacion || null}
          tipoMedida={localMedida.informacion?.tipo_medidas || []}
          setToast={setToast}
          etapaId={localMedida.etapa_id}
          isEditable={isEditable}
        />
      )}

      {existActoAdmin ? (
        <Documentos
          documentos={documentos}
          etapaId={localMedida.etapa_id}
          radicado={radicado}
          idAuxiliar={idAuxiliar}
          tipoEtapa="detalle_medida_preventiva"
          tiposDocumento={TIPOS_DOCUMENTO}
          setToast={setToast}
          isEditable={isEditable}
          onDocumentosUpdate={handleDocumentosUpdate}
        />
      ) : (
        isEditable && (
          <div className="card bg-base-100 shadow-xl w-full border border-warning/30">
            <div className="card-body">
              <div className="flex items-center gap-4">
                <div className="bg-warning/10 rounded-full p-3">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-8 w-8 text-warning"
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
                <div>
                  <h3 className="text-lg font-semibold">
                    Información y documentos no disponibles
                  </h3>
                  <p className="text-sm text-base-content/70 mt-1">
                    Debe crear un acto administrativo antes de registrar información o subir documentos.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )
      )}
    </div>
  );
}
