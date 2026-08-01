import { useCallback, useEffect, useRef, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import CierreActo from "./Cierre/CierreActo";


type CierreEtapaData = {
  id: number;
  expediente_id: number;
  acto_administrativo_id: number | null;
  fecha_creacion: string;
  acto_admin: any | null; // formato ActoAdmin-compatible (sancionatoria) desde el backend
};

type Props = {
  expedienteId: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
  onStageUpdate: (stage: string) => void;
  isEditable?: boolean;
  onArchiveSuccess?: () => void;
};

const STAGE_NAME = "Cierre";


export default function Cierre({
  expedienteId,
  setToast,
  onStageUpdate,
  isEditable = true,
  onArchiveSuccess,
}: Props) {
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [showLoading, setShowLoading] = useState(false);
  const [cierreData, setCierreData] = useState<CierreEtapaData | null>(null);
  const [creable, setCreable] = useState(false);
  const [creableMsg, setCreableMsg] = useState<string | null>(null);
  const [isCreatingStage, setIsCreatingStage] = useState(false);
  const [showArchiveModal, setShowArchiveModal] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchCierreData = useCallback(async () => {
    if (!expedienteId) { setIsLoadingData(false); return; }
    try {
      setIsLoadingData(true);
      loadingTimerRef.current = setTimeout(() => setShowLoading(true), 300);

      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_GET_CIERRE(expedienteId),
        { method: "GET" },
      );

      if (res.status === 404) {
        setCierreData(null);
        setCreable(res.creable ?? false);
        setCreableMsg(res.creable_msg ?? null);
        return;
      }
      if (res.ok) {
        setCierreData(res.data as CierreEtapaData);
      } else {
        setToast({ id: Date.now(), message: "Error al cargar la etapa de cierre", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error de conexión al cargar el cierre", type: "error" });
    } finally {
      setIsLoadingData(false);
      setShowLoading(false);
      if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current);
    }
  }, [expedienteId]);

  useEffect(() => {
    fetchCierreData();
    return () => { if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current); };
  }, [expedienteId]);

  const handleCreateStage = async () => {
    setIsCreatingStage(true);
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_CREATE_CIERRE(expedienteId),
        { method: "POST" },
      );
      if (res.ok) {
        setToast({ id: Date.now(), message: "Etapa de cierre creada correctamente", type: "success" });
        await fetchCierreData();
        onStageUpdate(STAGE_NAME);
      } else {
        setToast({ id: Date.now(), message: res.detail || "Error al crear la etapa", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error de conexión", type: "error" });
    } finally {
      setIsCreatingStage(false);
    }
  };

  const handleArchiveConfirm = async () => {
    setIsArchiving(true);
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_ARCHIVE(expedienteId),
        { method: "PATCH" },
      );
      if (res.ok) {
        setToast({ id: Date.now(), message: "Expediente archivado exitosamente", type: "success" });
        setShowArchiveModal(false);
        onStageUpdate(STAGE_NAME);
        onArchiveSuccess?.();
      } else {
        setToast({ id: Date.now(), message: res.detail || "Error al archivar el expediente", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error de conexión", type: "error" });
    } finally {
      setIsArchiving(false);
    }
  };

  const notifsCierre: any[] = cierreData?.acto_admin?.notificacion?.involucrados ?? [];
  const todasNotificadas =
    !!cierreData?.acto_admin &&
    notifsCierre.length > 0 &&
    notifsCierre.every((n: any) => n.notificacion_exitosa === true);

  // ── Loading ──
  if (isLoadingData && showLoading) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <span className="loading loading-spinner loading-lg text-primary" />
            <p className="text-gray-600 font-medium">Cargando datos...</p>
            <p className="text-sm text-gray-500">
              Obteniendo información de la etapa {STAGE_NAME}. Esto puede tardar unos segundos.
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
          <p>Seleccione un expediente para ver{isEditable ? " o editar" : ""} sus datos</p>
        </div>
      </div>
    );
  }

  if (isLoadingData) return <div className="min-h-[200px]" />;

  // ── Etapa no existe + no editable ──
  if (!cierreData && !isEditable) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-gray-400 to-gray-500 rounded-full p-4 shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-white" fill="none"
                viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div className="text-center space-y-3">
              <p className="text-gray-600 max-w-md mx-auto">
                Este expediente aún no tiene la etapa de{" "}
                <span className="font-semibold text-gray-700 whitespace-nowrap">"{STAGE_NAME}"</span>.
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

  // ── Etapa no existe + no creable ──
  if (!cierreData && !creable) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-warning/30">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-warning to-orange-500 rounded-full p-4 shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-white" fill="none"
                viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div className="text-center space-y-3">
              <h3 className="text-lg font-semibold">No es posible gestionar o crear esta etapa</h3>
              <div className="bg-warning/10 border border-amber-200 rounded-lg p-4 max-w-lg mx-auto">
                <p className="text-sm font-medium">
                  <span className="font-semibold text-warning">Motivo:</span>{" "}
                  {creableMsg ?? "No se cumplen los requisitos para crear esta etapa"}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Etapa no existe + creable ──
  if (!cierreData && creable) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-blue-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-full p-4 shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-white" fill="none"
                viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
              </svg>
            </div>
            <div className="text-center space-y-3">
              <p className="text-gray-600 max-w-md mx-auto">
                Este expediente aún no tiene la etapa de{" "}
                <span className="font-semibold text-blue-400 whitespace-nowrap">"{STAGE_NAME}"</span>.
              </p>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                Para continuar, cree esta etapa y registre el acto administrativo de cierre.
              </p>
            </div>
            <button
              className="btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
              onClick={handleCreateStage}
              disabled={isCreatingStage}
            >
              {isCreatingStage ? (
                <><span className="loading loading-spinner loading-sm" />Creando etapa...</>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
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

  if (!cierreData) return null;

  // ── Etapa existe ──
  return (
    <div className="space-y-6">
      {/* Acto + Notificaciones */}
      <CierreActo
        etapaCierreId={cierreData.id}
        expedienteId={expedienteId}
        actoAdmin={cierreData.acto_admin as unknown as any}
        isEditable={isEditable}
        setToast={setToast}
        onDataUpdated={fetchCierreData}
      />

      {/* Archivar — solo si todos notificados exitosamente */}
      {todasNotificadas && isEditable && (
        <div className="card bg-warning/5 shadow-lg">
          <div className="card-body">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-warning/20 rounded-full flex items-center justify-center flex-shrink-0">
                  <svg className="w-6 h-6 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                  </svg>
                </div>
                <div>
                  <h3 className="font-bold text-lg mb-1">Archivar Expediente</h3>
                  <p className="text-sm text-base-content/70">
                    Todos los involucrados han sido notificados exitosamente. Puede archivar este expediente.
                    Los expedientes archivados seguirán disponibles para consulta.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowArchiveModal(true)}
                className="btn btn-warning text-white gap-2 shadow-md hover:shadow-lg transition-all whitespace-nowrap"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
                Archivar Expediente
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal confirmación archivo */}
      {showArchiveModal && (
        <div className="modal modal-open">
          <div className="modal-box">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-warning/10 rounded-full flex items-center justify-center">
                <svg className="w-5 h-5 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h3 className="font-bold text-lg">Confirmar archivo del expediente</h3>
            </div>
            <p className="text-base-content/80 mb-4">
              Esta acción archivará el expediente. El expediente dejará de aparecer en la lista activa
              pero seguirá disponible para consulta.
            </p>
            <p className="text-sm font-medium text-base-content">¿Está seguro de que desea continuar?</p>
            <div className="modal-action">
              <button
                className="btn btn-outline"
                onClick={() => setShowArchiveModal(false)}
                disabled={isArchiving}
              >
                Cancelar
              </button>
              <button
                className="btn btn-warning text-white gap-2"
                onClick={handleArchiveConfirm}
                disabled={isArchiving}
              >
                {isArchiving ? (
                  <><span className="loading loading-spinner loading-sm" />Archivando...</>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                    </svg>
                    Sí, archivar
                  </>
                )}
              </button>
            </div>
          </div>
          <div className="modal-backdrop" onClick={() => !isArchiving && setShowArchiveModal(false)} />
        </div>
      )}
    </div>
  );
}
