import { useCallback, useEffect, useRef, useState } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import ConceptoDataCard from "./Concepto/ConceptoData";
import AutoRequerimiento from "./Concepto/AutoRequerimiento";
import OficioRemiteCard from "./Concepto/OficioRemiteCard";
import SolicitudInformacionCard from "./Concepto/SolicitudInformacionCard";


type ConceptoEtapaData = {
  id: number;
  expediente_id: number;
  tipo_acogida_concepto: "AUTO_REQUERIMIENTO" | "OFICIO" | "RESOLUCION_ARCHIVO";
  dias_termino: number | null;
  fecha_termino_calculada: string | null;
  acto_administrativo_id: number | null;
  fecha_creacion: string;
  acto_admin: any | null; // formato ActoAdmin-compatible (sancionatoria) desde el backend
  oficio_remite: {
    id: number;
    radicado: string;
    fecha_radicado: string;
    fecha_remitido: string;
    archivo_remite_id: number;
  } | null;
  solicitud_informacion: {
    id: number;
    radicado: string;
    fecha_radicado: string;
    archivo_solicitud_id: number;
  } | null;
};


type Props = {
  expedienteId: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
  onStageUpdate: (stage: string) => void;
  isEditable?: boolean;
};

const STAGE_NAME = "Concepto";

const TIPO_OPTIONS: { value: string; label: string }[] = [
  { value: "AUTO_REQUERIMIENTO", label: "Auto de Requerimiento" },
  { value: "OFICIO", label: "Oficio remitido por competencia" },
  { value: "RESOLUCION_ARCHIVO", label: "Resolución de Archivo, se cierra el trámite" },
];


export default function Concepto({
  expedienteId,
  setToast,
  onStageUpdate,
  isEditable = true,
}: Props) {
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [showLoading, setShowLoading] = useState(false);
  const [conceptoData, setConceptoData] = useState<ConceptoEtapaData | null>(null);
  const [creable, setCreable] = useState(false);
  const [creableMsg, setCreableMsg] = useState<string | null>(null);
  const [isCreatingStage, setIsCreatingStage] = useState(false);
  const [selectedTipoCrear, setSelectedTipoCrear] = useState<string>("");
  const [isSubmittingCreate, setIsSubmittingCreate] = useState(false);
  const loadingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchConceptoData = useCallback(async () => {
    if (!expedienteId) {
      setIsLoadingData(false);
      return;
    }
    try {
      setIsLoadingData(true);
      loadingTimerRef.current = setTimeout(() => setShowLoading(true), 300);

      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_GET_CONCEPTO(expedienteId),
        { method: "GET" },
      );

      if (res.status === 404) {
        setConceptoData(null);
        setCreable(res.creable ?? false);
        setCreableMsg(res.creable_msg ?? null);
        return;
      }

      if (res.ok) {
        setConceptoData(res.data as ConceptoEtapaData);
        setCreable(true);
      } else {
        setToast({ id: Date.now(), message: "Error al cargar la etapa concepto", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error de conexión al cargar el concepto", type: "error" });
    } finally {
      setIsLoadingData(false);
      setShowLoading(false);
      if (loadingTimerRef.current) clearTimeout(loadingTimerRef.current);
    }
  }, [expedienteId]);

  useEffect(() => {
    fetchConceptoData();
  }, [expedienteId]);

  const handleCreateStage = async () => {
    if (!selectedTipoCrear) {
      setToast({ id: Date.now(), message: "Seleccione el tipo de acogida", type: "error" });
      return;
    }
    setIsSubmittingCreate(true);
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_CREATE_CONCEPTO(expedienteId),
        {
          method: "POST",
          body: JSON.stringify({ tipo_acogida_concepto: selectedTipoCrear }),
        },
      );
      if (res.ok) {
        setToast({ id: Date.now(), message: "Etapa concepto creada correctamente", type: "success" });
        setIsCreatingStage(false);
        setSelectedTipoCrear("");
        await fetchConceptoData();
        onStageUpdate(STAGE_NAME);
      } else {
        setToast({ id: Date.now(), message: res.detail || "Error al crear la etapa", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error de conexión", type: "error" });
    } finally {
      setIsSubmittingCreate(false);
    }
  };

  const handleTipoUpdated = useCallback(
    async (_nuevoTipo: string) => {
      await fetchConceptoData();
      onStageUpdate(STAGE_NAME);
    },
    [fetchConceptoData, onStageUpdate],
  );

  const handleDataUpdated = useCallback(async () => {
    await fetchConceptoData();
  }, [fetchConceptoData]);

  // ── Loading ──
  if (isLoadingData && showLoading) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-12 space-y-4">
            <span className="loading loading-spinner loading-lg text-primary" />
            <p className="text-gray-600 font-medium">Cargando datos...</p>
            <p className="text-sm text-gray-500">
              Obteniendo información de la etapa concepto. Esto puede tardar unos segundos.
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
  if (!conceptoData && !isEditable) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-gray-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-gray-400 to-gray-500 rounded-full p-4 shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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

  // ── Etapa no existe + editable pero no creable ──
  if (!conceptoData && !creable && !isCreatingStage) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-warning/30">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-warning to-orange-500 rounded-full p-4 shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
              <p className="text-sm opacity-70 max-w-md mx-auto mt-4">
                Por favor, complete los requisitos necesarios antes de crear esta etapa.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Etapa no existe + editable + creable → crear ──
  if (!conceptoData && !isCreatingStage) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-blue-200">
        <div className="card-body">
          <div className="flex flex-col items-center justify-center py-8 space-y-6">
            <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-full p-4 shadow-lg">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div className="text-center space-y-3">
              <p className="text-gray-600 max-w-md mx-auto">
                Este expediente aún no tiene la etapa de{" "}
                <span className="font-semibold text-blue-500 whitespace-nowrap">"{STAGE_NAME}"</span>.
              </p>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                Para continuar, debe crear esta etapa indicando cómo se acoge el concepto técnico.
              </p>
            </div>
            <button
              className="btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
              onClick={() => setIsCreatingStage(true)}
            >
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
              </svg>
              Crear Etapa
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Modal de creación (selección de tipo) ──
  if (!conceptoData && isCreatingStage) {
    return (
      <div className="card bg-base-100 shadow-xl w-full border border-blue-200">
        <div className="card-body">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-warning/10 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold">Nueva Etapa — {STAGE_NAME}</h3>
              <p className="text-sm text-base-content/60">¿Cómo desea acoger el concepto técnico?</p>
            </div>
          </div>

          <div className="space-y-3 mb-6">
            {TIPO_OPTIONS.map((opt) => (
              <label
                key={opt.value}
                className={`flex items-start gap-3 p-4 rounded-xl border-2 cursor-pointer transition-all ${
                  selectedTipoCrear === opt.value
                    ? "border-warning bg-warning/5"
                    : "border-base-300 hover:border-warning/40"
                }`}
              >
                <input
                  type="radio"
                  name="tipo_acogida_crear"
                  value={opt.value}
                  checked={selectedTipoCrear === opt.value}
                  onChange={() => setSelectedTipoCrear(opt.value)}
                  className="radio radio-warning mt-0.5"
                  disabled={isSubmittingCreate}
                />
                <span className="text-sm font-medium">{opt.label}</span>
              </label>
            ))}
          </div>

          <div className="flex gap-3 justify-end border-t border-base-300 pt-4">
            <button
              className="btn btn-outline"
              onClick={() => { setIsCreatingStage(false); setSelectedTipoCrear(""); }}
              disabled={isSubmittingCreate}
            >
              Cancelar
            </button>
            <button
              className="btn btn-success text-white gap-2"
              onClick={handleCreateStage}
              disabled={!selectedTipoCrear || isSubmittingCreate}
            >
              {isSubmittingCreate ? (
                <><span className="loading loading-spinner loading-sm" />Creando...</>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
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

  // ── Etapa existe: mostrar contenido ──
  if (!conceptoData) return null;

  return (
    <div className="space-y-6">
      {/* Solicitud de información — independiente del tipo de acogida, se puede agregar en cualquier momento */}
      <SolicitudInformacionCard
        etapaConceptoId={conceptoData.id}
        expedienteId={expedienteId}
        solicitud={conceptoData.solicitud_informacion}
        isEditable={isEditable}
        setToast={setToast}
        onSaved={handleDataUpdated}
      />

      {/* Tipo de acogida */}
      <ConceptoDataCard
        etapaConceptoId={conceptoData.id}
        expedienteId={expedienteId}
        tipoActual={conceptoData.tipo_acogida_concepto}
        isEditable={isEditable}
        setToast={setToast}
        onTipoUpdated={handleTipoUpdated}
      />

      {/* Sub-flujo según tipo */}

      {conceptoData.tipo_acogida_concepto === "AUTO_REQUERIMIENTO" && (
        <AutoRequerimiento
          etapaConceptoId={conceptoData.id}
          expedienteId={expedienteId}
          actoAdmin={conceptoData.acto_admin}
          diasTermino={conceptoData.dias_termino}
          fechaTerminoCalculada={conceptoData.fecha_termino_calculada}
          isEditable={isEditable}
          setToast={setToast}
          onDataUpdated={handleDataUpdated}
        />
      )}

      {conceptoData.tipo_acogida_concepto === "OFICIO" && (
        <OficioRemiteCard
          etapaConceptoId={conceptoData.id}
          expedienteId={expedienteId}
          oficio={conceptoData.oficio_remite}
          isEditable={isEditable}
          setToast={setToast}
          onSaved={handleDataUpdated}
        />
      )}

      {conceptoData.tipo_acogida_concepto === "RESOLUCION_ARCHIVO" && (
        <div className="card bg-base-100 shadow-md border border-base-300">
          <div className="card-body">
            <div className="flex items-center gap-4 py-4">
              <div className="w-12 h-12 bg-error/10 rounded-full flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                </svg>
              </div>
              <div>
                <h4 className="font-bold text-base">Trámite Archivado</h4>
                <p className="text-sm text-base-content/60 mt-1">
                  El concepto técnico fue acogido mediante{" "}
                  <span className="font-semibold text-error">Resolución de Archivo</span>.
                </p>
                <p className="text-xs text-base-content/40 mt-2">
                  Creado: {new Date(conceptoData.fecha_creacion).toLocaleDateString("es-CO")}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
