import { useEffect, useState, useCallback, useRef } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import type {
  TipoNotificacion,
  Involved,
} from "../../../types/sancionatorioApp";
import ActoAdmin from "./ActoAdmin/ActoAdmin";
import Documentos from "./Document/Document";

type DocumentoData = {
  id: number;
  nombre: string;
  url_documento: string;
  fecha_subida: string;
};

type Props = {
  radicado: string;
  expedienteId: number;
  onStageUpdate: (stage: string) => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
  inicio_proceso: any;
  tiposNotificacion: TipoNotificacion[];
  involucrados: Involved[];
};

const STAGE_NAME = "INICIO PROCESO SANCIONATORIO";
const TIPOS_DOCUMENTO = [
  "Concepto Tecnico",
  "Respuesta Entidad Oficial",
  "Respuesta Infractor",
];

export default function StartSanctioningProcess({
  radicado,
  expedienteId,
  setToast,
  onStageUpdate,
  isEditable = true,
  inicio_proceso,
  tiposNotificacion = [],
  involucrados = [],
}: Props) {
  const [isCreatingStage, setIsCreatingStage] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [showLoading, setShowLoading] = useState(false);
  const [localInicioProceso, setLocalInicioProceso] = useState(
    inicio_proceso || null,
  );
  const [existActoAdmin, setExistActoAdmin] = useState<boolean>(false);
  const [documentos, setDocumentos] = useState<DocumentoData[]>([]);
  const loadingTimerRef = useRef<NodeJS.Timeout | null>(null);

  const fetchInicioProceso = useCallback(async () => {
    if (!expedienteId) {
      setIsLoadingData(false);
      return;
    }

    try {
      setIsLoadingData(true);

      // Solo mostrar loading si tarda más de 300ms
      loadingTimerRef.current = setTimeout(() => {
        setShowLoading(true);
      }, 300);

      const res = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_START_PROCESS(expedienteId),
        { method: "GET" },
      );

      if (res.ok) {
        setLocalInicioProceso(res.inicio_proceso);
        setDocumentos(res.inicio_proceso?.documento || []);

        if (res.inicio_proceso?.acto_admin?.id) {
          setExistActoAdmin(true);
        } else {
          setExistActoAdmin(false);
        }
      } else {
        setToast({
          id: Date.now(),
          message:
            res.detail ||
            "Error al cargar el inicio del proceso sancionatorio.",
          type: "error",
        });
      }
    } catch (e) {
      /* console.error("Error fetching inicio proceso:", e); */
      setToast({
        id: Date.now(),
        message: "Error al cargar el inicio del proceso sancionatorio.",
        type: "error",
      });
    } finally {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
      setShowLoading(false);
      setIsLoadingData(false);
    }
  }, [expedienteId, setToast]);

  useEffect(() => {
    fetchInicioProceso();

    return () => {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
    };
  }, [fetchInicioProceso]);

  const inicioProcesoData =
    localInicioProceso?.inicio_proceso || localInicioProceso;
  const stageExists = inicioProcesoData && inicioProcesoData.etapa_id;
  const tipoEtapaId = localInicioProceso?.tipo_etapa_id || null;

  const createStage = async () => {
    if (!expedienteId) {
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
        API_CONFIG.ENDPOINTS.FILE_CREATE_STAGE(expedienteId, tipoEtapaId),
        { method: "POST" },
      );

      if (res.ok && res.etapa_id) {
        const nuevoInicioProceso = {
          etapa_id: res.etapa_id,
          acto_admin: {},
          documento: [],
          tipo_etapa_id: tipoEtapaId,
        };
        setLocalInicioProceso(nuevoInicioProceso);
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
    [],
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
              Obteniendo información del inicio del proceso sancionatorio
            </p>
          </div>
        </div>
      </div>
    );
  }

  // No File Selected
  if (!expedienteId) {
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
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
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
  if (!stageExists) {
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
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
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
                Para continuar, debe crear esta etapa y así poder gestionar las
                notificaciones correspondientes.
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
        actoAdmin={inicioProcesoData.acto_admin || {}}
        etapaId={inicioProcesoData.etapa_id}
        tipoEtapa="inicio_proceso_sancionatorio"
        setToast={setToast}
        tipoActo="notificacion"
        isEditable={isEditable}
        involucrados={involucrados}
        tiposNotificacion={tiposNotificacion}
        setExistActoAdmin={setExistActoAdmin}
      />

      {existActoAdmin ? (
        <Documentos
          documentos={documentos}
          etapaId={inicioProcesoData.etapa_id}
          radicado={radicado}
          tipoEtapa="inicio_proceso_sancionatorio"
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
                    Documentos no disponibles
                  </h3>
                  <p className="text-sm text-base-content/70 mt-1">
                    Debe crear un acto administrativo antes de subir documentos.
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
