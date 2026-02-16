import type { BasicFile, Town, File, TipoNotificacion } from "../../types";
import { useState, useEffect, lazy, Suspense } from "react";
import { API_CONFIG, apiCall } from "../../utils/api";

const Information = lazy(() => import("./Stages/InformationStage"));
const PreliminaryInvestigation = lazy(
  () => import("./Stages/PreliminaryInvestigation"),
);
const PreventiveMeasure = lazy(() => import("./Stages/PreventiveMeasure"));
const StartSanctioningProcess = lazy(
  () => import("./Stages/StartSanctioningProcess"),
);
const CessationStage = lazy(() => import("./Stages/CessationStage"));
const FormulationCharges = lazy(() => import("./Stages/FormulationCharges"));
const OpeningProbationaryPeriod = lazy(
  () => import("./Stages/OpeningProbationaryPeriod"),
);
const ClosingProbationaryPeriod = lazy(
  () => import("./Stages/ClosingProbationaryPeriod"),
);
const SubstantiveDecision = lazy(() => import("./Stages/SubstantiveDecision"));
const Resource = lazy(() => import("./Stages/Resource"));
const ExecutionOfSanction = lazy(() => import("./Stages/ExecutionSanction"));

type Tab = {
  id: string;
  label: string;
  icon: string;
  component: React.LazyExoticComponent<React.ComponentType<any>>;
};

type Props = {
  file: BasicFile | null;
  towns: Town[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  resources: { id: number; name: string }[];
  onFileUpdate?: (updatedFile: BasicFile) => void;
  isEditable?: boolean;
  onArchiveSuccess?: () => void;
};

export default function FileDetail({
  file,
  towns,
  setToast,
  resources,
  onFileUpdate,
  isEditable = true,
  onArchiveSuccess,
}: Props) {
  const [activeTab, setActiveTab] = useState<string>("info");
  const [currentFile, setCurrentFile] = useState<BasicFile | null>(file);
  const [fullFile, setFullFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [tipoNotificacion, setTipoNotificacion] =
    useState<TipoNotificacion | null>(null);
  const [isTabsCollapsed, setIsTabsCollapsed] = useState(false);
  const [isDownloadingAll, setIsDownloadingAll] = useState(false);
  const [etapasExistentes, setEtapasExistentes] = useState<number[]>([]);

  // Sincronizar cuando cambia el file desde el padre
  useEffect(() => {
    setCurrentFile(file);
  }, [file]);

  // Cargar datos adicionales y combinar con BasicFile para crear File completo
  useEffect(() => {
    const fetchAndCombineFileData = async () => {
      if (!file) {
        setFullFile(null);
        return;
      }

      setLoading(true);
      try {
        const response = await apiCall(
          API_CONFIG.ENDPOINTS.FILE_FUll(file.radicado),
        );

        if (!response.ok) {
          throw new Error("Error al cargar datos del expediente");
        }

        if (response.ok && response.data) {
          setTipoNotificacion(response.tipo_notificacion);
          setEtapasExistentes(response.etapas_existentes || []);
          const information = response.data;

          const completeFile: File = {
            // Datos básicos del BasicFile
            radicado: file.radicado,
            nombre: file.nombre,
            fecha_creacion: file.fecha_creacion,
            municipio: file.municipio,
            archivado: file.archivado,

            // Datos adicionales del endpoint /file/full
            direccion: information.direccion || file.direccion,
            vereda: information.vereda || { id: 0, name: "Sin vereda" },
            id_auxiliar: information.id_auxiliar || 0,
            ultima_etapa: information.ultima_etapa || null,
            recurso_afectado: information.recurso_afectado || [],
            motivo_afectacion: information.motivo_afectacion || "",

            involucrados:
              information.involucrados && information.involucrados.length > 0
                ? information.involucrados
                : file.involucrados,
          };

          setFullFile(completeFile);
        } else {
          setToast({
            id: Date.now(),
            message: "No se encontraron datos adicionales del expediente",
            type: "error",
          });
        }
      } catch (error) {
        console.error("Error al cargar expediente completo:", error);
        setToast({
          id: Date.now(),
          message: "Error al cargar información completa del expediente",
          type: "error",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchAndCombineFileData();
  }, [file, setToast]);

  // Mapping de tab.id a tipo_etapa_id
  const tabToEtapaMap: { [key: string]: number | null } = {
    info: null, // Información siempre visible
    indagacion: 2,
    detalle: 1, // Medida Preventiva
    inicio: 9,
    cesacion: 10,
    cargos: 4,
    apertura_ep: 5,
    cierre_ep: 11,
    decision: 6,
    recurso: 12,
    ejecucion: 7,
  };

  const tabs: Tab[] = [
    {
      id: "info",
      label: "Información",
      icon: "bx-info-circle",
      component: Information,
    },
    {
      id: "indagacion",
      label: "Indagación Preliminar",
      icon: "bx-search-alt",
      component: PreliminaryInvestigation,
    },
    {
      id: "detalle",
      label: "Medida Preventiva",
      icon: "bx-error-alt",
      component: PreventiveMeasure,
    },
    {
      id: "inicio",
      label: "Inicio Proceso Sancionatorio",
      icon: "bx-book-bookmark",
      component: StartSanctioningProcess,
    },
    {
      id: "cesacion",
      label: "Cesacion",
      icon: "bx-error-alt",
      component: CessationStage,
    },
    {
      id: "cargos",
      label: "Formulación de Cargos",
      icon: "bx-file",
      component: FormulationCharges,
    },
    {
      id: "apertura_ep",
      label: "Apertura Etapa Probatoria",
      icon: "bx-cabinet",
      component: OpeningProbationaryPeriod,
    },
    {
      id: "cierre_ep",
      label: "Cierre Etapa Probatoria",
      icon: "bx-cabinet",
      component: ClosingProbationaryPeriod,
    },
    {
      id: "decision",
      label: "Decisión de Fondo",
      icon: "bx-check-circle",
      component: SubstantiveDecision,
    },
    {
      id: "recurso",
      label: "Probatoria del Recurso",
      icon: "bx-calendar-check",
      component: Resource,
    },
    {
      id: "ejecucion",
      label: "Ejecución Sanción",
      icon: "bx-calendar-check",
      component: ExecutionOfSanction,
    },
  ];

  // Verificar si una etapa existe en el expediente
  const isEtapaDisponible = (tabId: string): boolean => {
    const etapaId = tabToEtapaMap[tabId];
    if (etapaId === null) return true; // Info siempre disponible
    if (!isEditable) {
      // En modo consulta, verificar disponibilidad solo si hay datos de etapas
      if (etapasExistentes.length === 0) {
        // Si no hay datos de etapas existentes, permitir acceso a todas (carga inicial)
        return true;
      }
      // Si hay datos, solo permitir acceso a las etapas que existen
      return etapasExistentes.includes(etapaId);
    }
    return true; // En modo editable, todas disponibles
  };

  const handleTabClick = (tabId: string) => {
    if (!currentFile) return;
    // Verificar disponibilidad antes de cambiar
    if (!isEtapaDisponible(tabId)) {
      console.log(
        `[FileDetail] Intento de acceder a etapa no disponible: ${tabId}`,
      );
      return;
    }
    setActiveTab(tabId);
  };

  // Función para actualizar el File
  const handleFullFileUpdate = (updatedFile: File) => {
    setFullFile(updatedFile);

    // Propagar actualización al padre como BasicFile
    if (onFileUpdate) {
      const basicFile: BasicFile = {
        radicado: updatedFile.radicado,
        nombre: updatedFile.nombre,
        fecha_creacion: updatedFile.fecha_creacion,
        direccion: updatedFile.direccion,
        municipio: updatedFile.municipio,
        involucrados: updatedFile.involucrados,
        archivado: updatedFile.archivado,
      };
      onFileUpdate(basicFile);
    }
  };
  const handleStageUpdate = (stage: string) => {
    if (!fullFile) return;
    const updatedFile: File = {
      ...fullFile,
      ultima_etapa: stage,
    };
    setFullFile(updatedFile);
  };

  const handleDownloadAll = async () => {
    if (!currentFile) return;

    setIsDownloadingAll(true);

    const BASE_URL =
      (window as any).ENV?.VITE_API_URL ||
      import.meta.env.VITE_API_URL ||
      "http://localhost:8000";
    const url = `${BASE_URL}${API_CONFIG.ENDPOINTS.FILE_DOWNLOAD_ALL(
      currentFile.radicado,
    )}`;

    // Usar window.open igual que otras descargas - envía cookies automáticamente
    window.open(url, "_blank");

    // Simular progreso y mostrar mensaje después de un momento
    setTimeout(() => {
      setIsDownloadingAll(false);
      setToast({
        id: Date.now(),
        message: "Descarga iniciada exitosamente",
        type: "success",
      });
    }, 1500);
  };

  const renderTabContent = () => {
    if (!currentFile) {
      return (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-base-200 rounded-lg border-2 border-dashed border-base-300">
          <div className="w-16 h-16 bg-base-300 rounded-full flex items-center justify-center mb-4">
            <i className="bx bx-folder-open text-2xl text-base-content/40"></i>
          </div>
          <h2 className="text-xl font-medium text-base-content/70 mb-2">
            Sin expediente seleccionado
          </h2>
          <p className="text-base-content/50 max-w-sm">
            Selecciona un expediente para ver {isEditable ? "y gestionar" : ""}{" "}
            sus etapas
          </p>
        </div>
      );
    }

    if (loading || !fullFile) {
      return (
        <div className="flex justify-center items-center py-20">
          <div className="flex flex-col items-center gap-4">
            <span className="loading loading-spinner loading-lg text-success"></span>
            <p className="text-base-content/70">
              Cargando información completa...
            </p>
          </div>
        </div>
      );
    }

    const currentTab = tabs.find((tab) => tab.id === activeTab);
    if (!currentTab) return null;

    const Component = currentTab.component;

    // Props para los componentes con el File completo, indagacion y medida
    const commonProps = {
      file: fullFile,
      radicado: fullFile.radicado,
      idAuxiliar: fullFile.id_auxiliar,
      towns,
      resources,
      tiposNotificacion: tipoNotificacion,
      involucrados: fullFile.involucrados,
      onFileUpdate: handleFullFileUpdate,
      onStageUpdate: handleStageUpdate,
      setToast,
      isEditable,
      onArchiveSuccess,
    };

    return (
      <Suspense
        fallback={
          <div className="flex justify-center items-center py-20">
            <div className="flex flex-col items-center gap-4">
              <span className="loading loading-spinner loading-lg text-success"></span>
              <p className="text-base-content/70">Cargando contenido...</p>
            </div>
          </div>
        }
      >
        <Component {...commonProps} />
      </Suspense>
    );
  };

  // Obtener el tab activo actual
  const currentActiveTab = tabs.find((tab) => tab.id === activeTab);

  return (
    <div className="flex-1 flex flex-col h-full bg-base-200">
      <link
        href="https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css"
        rel="stylesheet"
      />

      {/* HEADER MEJORADO */}
      <div className="flex-shrink-0 bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm sticky top-0 z-10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
                <i className="bx bx-folder-open text-success text-xl"></i>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                  {currentFile ? "Expediente Activo" : "Panel"}
                </p>
                <h1 className="text-lg font-bold text-base-content">
                  {currentFile ? currentFile.radicado : "Panel de Expedientes"}
                </h1>
              </div>
            </div>
            {!isEditable && currentFile && (
              <div className="flex items-center gap-3">
                <button
                  onClick={handleDownloadAll}
                  disabled={isDownloadingAll}
                  className="btn btn-success gap-2 shadow-lg text-white font-medium hover:scale-105 transition-transform"
                  title="Descargar todos los documentos del expediente"
                >
                  {isDownloadingAll ? (
                    <>
                      <span className="loading loading-spinner loading-sm"></span>
                      Generando PDF...
                    </>
                  ) : (
                    <>
                      <i className="bx bx-download text-lg"></i>
                      Descargar Expediente
                    </>
                  )}
                </button>
                <button
                  className="btn btn-success text-white shadow-lg hover:scale-105 transition-transform"
                  title="Solo lectura"
                >
                  <i className="bx bx-show text-xl"></i>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* NAVEGACIÓN DE ETAPAS - COLAPSABLE */}
      {currentFile && (
        <div className="flex-shrink-0 bg-base-100 border-b border-base-300">
          {/* Barra colapsada - Muestra etapa actual */}
          {isTabsCollapsed && (
            <div className="px-4 py-3">
              <div className="container mx-auto max-w-7xl flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-success/20 rounded-full flex items-center justify-center flex-shrink-0">
                    <i
                      className={`bx ${currentActiveTab?.icon} text-success text-base`}
                    ></i>
                  </div>
                  <div>
                    <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                      Etapa Actual
                    </p>
                    <p className="text-sm font-semibold text-base-content">
                      {currentActiveTab?.label}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setIsTabsCollapsed(false)}
                  className="btn btn-ghost btn-sm gap-2"
                  title="Mostrar todas las etapas"
                >
                  <span className="text-xs">Mostrar etapas</span>
                  <i className="bx bx-chevron-down text-lg"></i>
                </button>
              </div>
            </div>
          )}

          {/* Barra expandida - Muestra todas las etapas */}
          {!isTabsCollapsed && (
            <div className="px-4 py-2">
              <div className="container mx-auto max-w-7xl">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                    Etapas del Proceso
                  </h2>
                  <button
                    onClick={() => setIsTabsCollapsed(true)}
                    className="btn btn-ghost btn-xs gap-1"
                    title="Ocultar etapas"
                  >
                    <span className="text-[10px]">Ocultar</span>
                    <i className="bx bx-chevron-up text-sm"></i>
                  </button>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-2">
                  {tabs.map((tab) => {
                    const isActive = activeTab === tab.id;
                    const disponible = isEtapaDisponible(tab.id);
                    return (
                      <button
                        key={tab.id}
                        onClick={() => handleTabClick(tab.id)}
                        disabled={!disponible}
                        className={`relative flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all duration-200 ${
                          !disponible
                            ? "bg-base-300/50 text-base-content/30 cursor-not-allowed opacity-50"
                            : isActive
                              ? "bg-success text-white shadow-md"
                              : "bg-base-200 text-base-content/70 hover:bg-base-300 hover:text-base-content"
                        }`}
                        title={
                          disponible
                            ? tab.label
                            : `${tab.label} (No disponible)`
                        }
                      >
                        <div
                          className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${
                            isActive ? "bg-white/20" : "bg-base-300"
                          }`}
                        >
                          <i
                            className={`bx ${tab.icon} text-sm ${
                              isActive ? "text-white" : "text-base-content/60"
                            }`}
                          ></i>
                        </div>

                        <span className="text-left text-[11px] leading-tight flex-1 truncate">
                          {tab.label}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* CONTENIDO PRINCIPAL */}
      <div className="flex-1 overflow-y-auto bg-base-200">
        <div className="container mx-auto p-6 max-w-7xl">
          <div className="bg-base-100 rounded-lg shadow-sm border border-base-300">
            <div className="p-8">
              <div>{renderTabContent()}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
