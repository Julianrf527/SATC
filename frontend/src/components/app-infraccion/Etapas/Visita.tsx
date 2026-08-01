import { apiCall, API_CONFIG } from "../../../utils/api";
import type { InformeTecnico } from "../../../types/infraccionApp";
import { useCallback, useEffect, useState, useRef } from "react";
import { openDocumentById } from "../../../utils/documentViewer";

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

const STAGE_NAME = "Visita Técnica";

const formatDate = (d: string | null | undefined) => {
  if (!d) return "—";
  const [year, month, day] = d.split("T")[0].split("-");
  return `${day}/${month}/${year}`;
};

export default function VisitStage({
  expedienteId,
  setToast,
  onStageUpdate,
  isEditable,
}: Props) {
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [showLoading, setShowLoading] = useState(false);
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [informeTecnico, setInformeTecnico] = useState<InformeTecnico | null>(
    null,
  );
  const [isCreable, setIsCreable] = useState(false);
  const [creableMsg, setCreableMsg] = useState<string | null>(null);

  const handleCreateStage = async () => {
    try {
      setIsLoadingData(true);
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_CREATE_REPORT(expedienteId, "VISITA"),
        { method: "POST" },
      );
      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Etapa creada exitosamente",
          type: "success",
        });
        fetchReport();
        onStageUpdate(STAGE_NAME);
        setIsCreable(false);
        setInformeTecnico(res.data);
      } else {
        setToast({
          id: Date.now(),
          message: res.error || "Error al crear la etapa",
          type: "error",
        });
      }
    } catch (error) {
      setToast({
        id: Date.now(),
        message: "Error al crear la etapa",
        type: "error",
      });
    } finally {
      setIsLoadingData(false);
    }
  };

  const fetchReport = useCallback(async () => {
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
        API_CONFIG.ENDPOINTS.INFRACTION_GET_REPORT(expedienteId, "VISITA"),
        { method: "GET" },
      );
      if (res.status === 404) {
        setInformeTecnico(null);
        setIsCreable(res.creable ?? false);
        setCreableMsg(res.creable_msg ?? null);
        return;
      }

      if (res.ok) {
        setInformeTecnico(res.data);
        setIsCreable(false);
        setCreableMsg(null);
      } else {
        setIsCreable(res.creable ?? false);
        setCreableMsg(res.creable_msg ?? null);
        setToast({
          id: Date.now(),
          message: res.error || "Error al cargar la visita técnica",
          type: "error",
        });
      }
    } catch (error) {
      setToast({
        id: Date.now(),
        message: "Error al cargar la visita técnica",
        type: "error",
      });
    } finally {
      if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current);
      setIsLoadingData(false);
    }
  }, [expedienteId]);

  useEffect(() => {
    if (expedienteId) {
      fetchReport();
    }
    return () => {
      if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current);
    };
  }, [expedienteId]);

  if (isLoadingData && showLoading) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <span className="loading loading-spinner loading-lg text-primary"></span>
            <p className="text-gray-600 font-medium">Cargando datos...</p>
            <p className="text-sm text-gray-500">
              Obteniendo información de la etapa visita técnica. Esto puede
              tardar unos segundos.
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

  if (!informeTecnico && !isEditable) {
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

  if (!informeTecnico && !isCreable) {
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
                  {creableMsg ?? "No se cumplen los requisitos para crear esta etapa"}
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

  if (!informeTecnico && isCreable) {
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
                etapa {STAGE_NAME} correspondiente.
              </p>
            </div>
            <button
              className="btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
              onClick={() => handleCreateStage()}
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

  if (informeTecnico && !informeTecnico.fecha_aceptacion_informe) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-yellow-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-4">
            <div className="bg-gradient-to-br from-yellow-400 to-yellow-500 rounded-full p-4 shadow-lg">
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
                  d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div className="text-center space-y-2">
              <h3 className="text-lg font-semibold text-yellow-700">
                {STAGE_NAME}
              </h3>
              <p className="text-gray-600 max-w-md mx-auto">
                El informe de visita técnica está en proceso.
              </p>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                Aún no ha sido aceptado. El seguimiento se gestiona desde{" "}
                <strong>Informes Técnicos</strong>.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        {/* HEADER */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-success"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold">Datos de la Visita Técnica</h3>
              <p className="text-sm text-base-content/60">Informe aceptado</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="badge badge-success text-white gap-1">
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Aceptado
            </span>
            {informeTecnico?.documento_informe_id && (
              <button
                onClick={() => openDocumentById(informeTecnico!.documento_informe_id!)}
                className="btn btn-success btn-sm text-white gap-2"
                title="Ver informe aceptado"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M15.5,15.5L13,19L11.5,15.5L8,14L11.5,12.5L13,9L14.5,12.5L18,14L15.5,15.5M13,3.5L17.5,8H13V3.5Z" />
                </svg>
                Ver Informe
              </button>
            )}
          </div>
        </div>

        {/* DATOS */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Profesional */}
          <div className="flex items-start gap-2">
            <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg
                className="w-4 h-4 text-base-content/70"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                Profesional Asignado
              </p>
              <p className="text-sm font-semibold">
                {informeTecnico?.profesional_nombre ?? (
                  <span className="text-base-content/40 italic">
                    Sin asignar
                  </span>
                )}
              </p>
            </div>
          </div>

          {/* Fecha programación */}
          <div className="flex items-start gap-2">
            <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg
                className="w-4 h-4 text-base-content/70"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 7V3m8 4V3m-9 8h10m-12 9h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v11a2 2 0 002 2z"
                />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                Fecha Programación
              </p>
              <p className="text-sm font-semibold">
                {formatDate(informeTecnico?.fecha_programacion_visita)}
              </p>
            </div>
          </div>

          {/* Fecha recibido */}
          <div className="flex items-start gap-2">
            <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg
                className="w-4 h-4 text-base-content/70"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                Fecha Recibido
              </p>
              <p className="text-sm font-semibold">
                {formatDate(informeTecnico?.fecha_recibido_informe)}
              </p>
            </div>
          </div>

          {/* Fecha aceptación */}
          <div className="flex items-start gap-2">
            <div className="w-8 h-8 bg-success/10 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
              <svg
                className="w-4 h-4 text-success"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M5 13l4 4L19 7"
                />
              </svg>
            </div>
            <div>
              <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                Fecha Aceptación
              </p>
              <p className="text-sm font-semibold text-success">
                {formatDate(informeTecnico?.fecha_aceptacion_informe)}
              </p>
            </div>
          </div>
        </div>

        {/* Nota */}
        <div className="mt-4 alert py-2 bg-base-200 border-0">
          <svg
            className="w-4 h-4 text-base-content/50 shrink-0"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <span className="text-xs text-base-content/60">
            La asignación de profesionales y el seguimiento del proceso se
            gestiona desde <strong>Informes Técnicos</strong>.
          </span>
        </div>
      </div>
    </div>
  );
}
