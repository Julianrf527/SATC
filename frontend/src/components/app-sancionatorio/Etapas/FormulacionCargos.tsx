import { useEffect, useState, useCallback, useRef } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import type { TipoNotificacion } from "../../../types/sancionatorioApp";
import ActoAdmin from "../../Common/ActoAdministrativo/ActoAdmin";
import Documentos from "./Document/Document";
import DataStageFormulation from "./FormulacionCargos/FormulacionCargosData";
import type { Involucrado } from "../../../types/involucradoApp";

type DocumentoData = {
  id: number;
  nombre: string;
  documento_anexo_id: number;
  fecha_subida: string;
};

type FormulationCharges = {
  id: number;
  descargos: boolean | null;
  url_documento?: string | null;
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
  // any: ver nota en DecisionFondo.tsx — sin contrato de forma estable por etapa.
  inicio_proceso: any;
  tiposNotificacion: TipoNotificacion[];
  involucrados: Involucrado[];
};

const STAGE_NAME = "FORMULACION DE CARGOS";
const TIPOS_DOCUMENTO = ["Informe Tecnico", "Anexos"];

export default function FormulacionCargos({
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
  const [localFormulacion, setLocalFormulacion] = useState(
    inicio_proceso || null,
  );
  const [existActoAdmin, setExistActoAdmin] = useState<boolean>(false);
  const [documentos, setDocumentos] = useState<DocumentoData[]>([]);
  const [formulationData, setFormulationData] = useState<
    FormulationCharges | undefined
  >();
  const [localCreable, setLocalCreable] = useState<{ status: boolean; msg: string } | null>(null);
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchFormulacion = useCallback(async () => {
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
        API_CONFIG.ENDPOINTS.FILE_FORMULATION(expedienteId),
        {
          method: "GET",
        },
      );

      if (res.ok) {
        setLocalFormulacion(res.formulacion_cargos);
        setDocumentos(res.formulacion_cargos?.documentos_anexos || []);
        setFormulationData(res.formulacion_cargos?.informacion);

        if (res.formulacion_cargos?.acto_admin?.id) {
          setExistActoAdmin(true);
        } else {
          setExistActoAdmin(false);
        }
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al cargar formulación de cargos.",
          type: "error",
        });
      }
    } catch (e) {
      setToast({
        id: Date.now(),
        message: "Error al cargar formulación de cargos.",
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
    fetchFormulacion();
    return () => {
      if (loadingTimerRef.current) {
        clearTimeout(loadingTimerRef.current);
      }
    };
  }, [fetchFormulacion]);

  const formulacionData = localFormulacion?.formulacion || localFormulacion;
  const stageExists = formulacionData && formulacionData.etapa_id;
  const creable = localCreable ?? formulacionData?.creable ?? localFormulacion?.creable ?? { status: true, msg: "" };

  const createStage = async () => {
    if (!expedienteId) {
      setToast({
        id: Date.now(),
        message: "No se ha seleccionado un expediente.",
        type: "error",
      });
      return;
    }

    try {
      setIsCreatingStage(true);

      const res = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_FORMULATION_CREATE(expedienteId),
        { method: "POST" },
      );

      if (res.ok && res.etapa_id) {
        const nuevaFormulacion = {
          etapa_id: res.etapa_id,
          acto_admin: {},
          documento: [],
          informacion: undefined,
          creable: { status: true, msg: "" },
        };
        setLocalFormulacion(nuevaFormulacion);
        setDocumentos([]);
        setFormulationData(undefined);
        setExistActoAdmin(false);
        onStageUpdate(STAGE_NAME);

        setToast({
          id: Date.now(),
          message: "Etapa creada exitosamente.",
          type: "success",
        });
      } else if (res.status && res.status < 500) {
        setLocalCreable({ status: false, msg: res.detail || "No se puede crear esta etapa." });
      } else {
        setToast({ id: Date.now(), message: "Error interno al crear la etapa.", type: "error" });
      }
    } catch (e) {
      setToast({ id: Date.now(), message: "Error al crear la etapa.", type: "error" });
    } finally {
      setIsCreatingStage(false);
    }
  };

  const handleDocumentosUpdate = useCallback(
    (updatedDocumentos: DocumentoData[]) => {
      setDocumentos(updatedDocumentos);
      fetchFormulacion();
    },
    [fetchFormulacion],
  );

  const handleFormulationUpdate = useCallback(() => {
    fetchFormulacion();
  }, [fetchFormulacion]);

  if (isLoadingData && showLoading) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <span className="loading loading-spinner loading-lg text-primary"></span>
            <p className="text-gray-600 font-medium">Cargando datos...</p>
            <p className="text-sm text-gray-500">
              Obteniendo información de la formulación de cargos
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

  if (!stageExists && isEditable && creable.status) {
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
                Para continuar, debe crear esta etapa y así poder gestionar la
                formulación de cargos correspondiente.
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

  if (stageExists) {
    return (
      <div className="space-y-6">
        <ActoAdmin
          expedienteId={expedienteId}
          actoAdmin={formulacionData.acto_admin || {}}
          etapaId={formulacionData.etapa_id}
        stageBinding={{ type: "etapa_san_formulacion_cargos", id: formulacionData.etapa_id }}
          tipoEtapa="etapa_formulacion_cargos"
          setToast={setToast}
          tipoActo="notificacion"
          isEditable={isEditable}
          involucrados={involucrados}
          tiposNotificacion={tiposNotificacion}
          setExistActoAdmin={setExistActoAdmin}
        />

        {/* Información de Formulación - Solo si existe acto admin */}
        {existActoAdmin && (
          <DataStageFormulation
            data={formulationData}
            setToast={setToast}
            etapaId={formulacionData.etapa_id}
            expedienteId={expedienteId}
            onDataUpdated={handleFormulationUpdate}
            isEditable={isEditable}
          />
        )}

        {/* Documentos - Solo si existe acto admin */}
        {existActoAdmin ? (
          <Documentos
            documentos={documentos}
            etapaId={formulacionData.etapa_id}
            expedienteId={expedienteId}
            tipoEtapa="etapa_formulacion_cargos"
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
                      Debe crear un acto administrativo antes de registrar
                      información o subir documentos.
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

  return null;
}
