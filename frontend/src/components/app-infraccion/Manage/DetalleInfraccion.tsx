import { useState, useEffect, lazy, Suspense } from "react";
import { API_CONFIG, apiCall } from "../../../utils/api";
import { downloadBlobFile } from "../../../utils/DownloadFile";
import "boxicons/css/boxicons.min.css";
import type {
  Expediente,
  ExpedienteDetalle,
  Quejoso,
  TipoAfectacion,
} from "../../../types/infraccionApp";
import type { Municipio, ModeloGenerico } from "../../../types/common";

const InformacionExpediente = lazy(
  () => import("../Etapas/InformacionInfraccion"),
);
const Respuesta = lazy(() => import("../Etapas/Respuesta"));
const Visita = lazy(() => import("../Etapas/Visita"));
const Concepto = lazy(() => import("../Etapas/Concepto"));
const Seguimiento = lazy(() => import("../Etapas/Seguimiento"));
const Cierre = lazy(() => import("../Etapas/Cierre"));

type Tab = {
  id: string;
  label: string;
  icon: string;
  component: React.LazyExoticComponent<React.ComponentType<any>>;
};

type Props = {
  expedienteSeleccionado: Expediente | null;
  municipioList: Municipio[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  recursoAfectadoList: ModeloGenerico[];
  tipoAfectacionList: TipoAfectacion[];
  quejosoList: Quejoso[];
  setQuejosoList?: (quejosos: Quejoso[]) => void;
  onUpdate?: (updated: Expediente) => void;
  isEditable?: boolean;
  onArchiveSuccess?: () => void;
};

export default function DetalleInfraccion({
  expedienteSeleccionado,
  municipioList,
  recursoAfectadoList,
  tipoAfectacionList,
  quejosoList,
  setQuejosoList,
  setToast,
  onUpdate,
  isEditable = true,
  onArchiveSuccess,
}: Props) {
  const [expedienteActual, setExpedienteActual] = useState<Expediente | null>(
    expedienteSeleccionado,
  );
  const [expedienteDetalle, setExpedienteDetalle] =
    useState<ExpedienteDetalle | null>(null);
  const [activeTab, setActiveTab] = useState<string>("info");
  const [loading, setLoading] = useState(false);
  const [tipoNotificacion, setTipoNotificacion] =
    useState<ModeloGenerico | null>(null);
  const [isTabsCollapsed, setIsTabsCollapsed] = useState(false);
  const [isDownloadingAll, setIsDownloadingAll] = useState(false);
  const [etapasExistentes, setEtapasExistentes] = useState<number[] | null>(null);

  useEffect(() => {
    setExpedienteActual(expedienteSeleccionado);
    if (!isEditable) setActiveTab("info");
  }, [expedienteSeleccionado]);

  // Cargar datos adicionales y combinar con Expediente para crear File completo
  useEffect(() => {
    let cancelado = false;

    const cargarExpedienteDetalle = async () => {
      if (!expedienteActual) {
        setExpedienteDetalle(null);
        return;
      }

      setLoading(true);
      setEtapasExistentes(null);
      try {
        const response = await apiCall(
          API_CONFIG.ENDPOINTS.INFRACTION_FUll(expedienteActual.id),
        );

        if (cancelado) return;

        if (!response.ok) {
          throw new Error("Error al cargar datos del expediente");
        }

        if (response.ok && response.data) {
          setTipoNotificacion(response.tipo_notificacion);
          setEtapasExistentes(response.etapas_existentes ?? []);
          const information = response.data;

          const expedienteDetalle: ExpedienteDetalle = {
            // Datos básicos del Expediente
            id: expedienteActual.id,
            radicado: expedienteActual.radicado,
            fecha_radicado: expedienteActual.fecha_radicado,
            municipio: expedienteActual.municipio,
            fecha_creacion: expedienteActual.fecha_creacion,
            archivado: expedienteActual.archivado,
            etapa_actual: expedienteActual.etapa_actual || null,

            // Datos adicionales del endpoint /file/full
            direccion: information.direccion || "",
            descripcion: information.descripcion || "",
            vereda: information.vereda || { id: 0, nombre: "Sin vereda" },
            quejosos: information.quejosos || [],
            tipos_afectacion: information.tipos_afectacion || [],
            recurso_afectado: information.recurso_afectado || [],
            radicados_asociados: information.radicados_asociados || [],

            involucrados:
              information.involucrados && information.involucrados.length > 0
                ? information.involucrados
                : expedienteActual.involucrados,
          };

          setExpedienteDetalle(expedienteDetalle);
        } else {
          setToast({
            id: Date.now(),
            message: "No se encontraron datos adicionales del expediente",
            type: "error",
          });
        }
      } catch (error) {
        if (cancelado) return;
        setEtapasExistentes([]);
        setToast({
          id: Date.now(),
          message: "Error al cargar información completa del expediente",
          type: "error",
        });
      } finally {
        if (!cancelado) setLoading(false);
      }
    };

    cargarExpedienteDetalle();

    return () => {
      cancelado = true;
    };
  }, [expedienteActual?.id, setToast]);

  const tabs: Tab[] = [
    {
      id: "info",
      label: "Información",
      icon: "bx-info-circle",
      component: InformacionExpediente,
    },
    {
      id: "respuesta",
      label: "Respuesta",
      icon: "bx-search-alt",
      component: Respuesta,
    },
    {
      id: "visita",
      label: "Visita Técnica",
      icon: "bx-error-alt",
      component: Visita,
    },
    {
      id: "concepto",
      label: "Acoger Concepto",
      icon: "bx-book-bookmark",
      component: Concepto,
    },
    {
      id: "seguimiento",
      label: "Visita Seguimiento",
      icon: "bx-error-alt",
      component: Seguimiento,
    },
    {
      id: "cierre",
      label: "Cierre Expediente",
      icon: "bx-check-circle",
      component: Cierre,
    },
  ];
  // Mapping de tab.id a tipo_etapa_id
  const tabToEtapaMap: { [key: string]: number | null } = {
    info: null, // Información siempre visible
    respuesta: 1,
    visita: 2,
    concepto: 3,
    seguimiento: 4,
    cierre: 5,
  };

  const isEtapaDisponible = (tabId: string): boolean => {
    const etapaId = tabToEtapaMap[tabId];
    if (etapaId === null) return true; // Info siempre disponible
    if (!isEditable) {
      if (etapasExistentes === null) return false; // Cargando: deshabilitar hasta saber
      return etapasExistentes.includes(etapaId);
    }
    return true; // En modo editable, todas disponibles
  };

  const handleTabClick = (tabId: string) => {
    if (!expedienteActual) return;
    if (!isEtapaDisponible(tabId)) {
      return;
    }
    setActiveTab(tabId);
  };

  const handleUpdate = (updated: ExpedienteDetalle) => {
    setExpedienteDetalle(updated);

    // Propagar actualización al padre como Expediente
    if (onUpdate) {
      const Expediente: Expediente = {
        id: updated.id,
        radicado: updated.radicado,
        fecha_radicado: updated.fecha_radicado,
        municipio: updated.municipio,
        fecha_creacion: updated.fecha_creacion,
        involucrados: updated.involucrados,
        etapa_actual: updated.etapa_actual || null,
        archivado: updated.archivado,
      };
      onUpdate(Expediente);
    }
  };
  const handleStageUpdate = (stage: string) => {
    if (!expedienteDetalle) return;
    const updated: ExpedienteDetalle = {
      ...expedienteDetalle,
      etapa_actual: stage,
    };
    setExpedienteDetalle(updated);
  };

  const handleDownloadAll = async () => {
    if (!expedienteDetalle) return;

    setIsDownloadingAll(true);

    try {
      const endpoint = API_CONFIG.ENDPOINTS.INFRACTION_DOWNLOAD_ALL(
        expedienteDetalle.id,
      );
      const filename = `expediente-${expedienteDetalle.radicado || expedienteDetalle.id}.pdf`;

      const result = await downloadBlobFile(endpoint, filename);

      if (!result.ok) {
        if (result.message) {
          setToast({
            id: Date.now(),
            message: result.message,
            type: "error",
          });
        }
        return;
      }

      setToast({
        id: Date.now(),
        message: "Descarga iniciada exitosamente",
        type: "success",
      });
    } catch {
      setToast({
        id: Date.now(),
        message: "Error al descargar el expediente",
        type: "error",
      });
    } finally {
      setIsDownloadingAll(false);
    }
  };

  const renderTabContent = () => {
    if (!expedienteDetalle) {
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

    if (loading || !expedienteDetalle) {
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
      expediente: expedienteDetalle,
      expedienteId: expedienteDetalle.id,
      municipioList: municipioList,
      recursoAfectadoList: recursoAfectadoList,
      tipoAfectacionList: tipoAfectacionList,
      quejosoList: quejosoList,
      setQuejosoList,
      tiposNotificacion: tipoNotificacion,
      involucrados: expedienteDetalle.involucrados,
      onUpdate: handleUpdate,
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

  const currentActiveTab = tabs.find((tab) => tab.id === activeTab);

  return (
    <div className="flex-1 flex flex-col h-full bg-base-200">
      {/* HEADER MEJORADO */}
      <div className="flex-shrink-0 bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
                <i className="bx bx-folder-open text-success text-xl"></i>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                  {expedienteActual ? "Expediente Activo" : "Panel"}
                </p>
                <h1 className="text-lg font-bold text-base-content">
                  {expedienteActual
                    ? expedienteActual.radicado
                    : "Panel de Expedientes"}
                </h1>
              </div>
            </div>
            {!isEditable && expedienteActual && (
              <div className="flex items-center gap-3">
                <div className="flex items-center gap-1.5 px-3 py-1.5 bg-success/10 border border-success/30 rounded-lg">
                  <i className="bx bx-show text-success text-base"></i>
                  <span className="text-xs font-semibold text-success uppercase tracking-wide">Modo Consulta</span>
                </div>
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
              </div>
            )}
          </div>
        </div>
      </div>

      {/* NAVEGACIÓN DE ETAPAS - COLAPSABLE */}
      {expedienteActual && (
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
