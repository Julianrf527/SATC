import type { Expediente, ExpedienteDetalle } from "@shared/types/sancionatorio";
import type { Municipio, ModeloGenerico } from "@shared/types/common";
import { useState, useEffect, useMemo, Suspense } from "react";
import { API_CONFIG } from "@shared/lib/api";
import { downloadBlobFile } from "@shared/lib/downloadFile";
import ErrorBoundary from "@shared/ui/ErrorBoundary";
import { useExpedienteFullQuery } from "../api/expediente";
import type { ExpedienteFullResponse, SetToast } from "../types";
import { ETAPAS_TABS } from "./etapasTabs";
import EtapasNavegacion from "./EtapasNavegacion";
import "boxicons/css/boxicons.min.css";

type Props = {
  expedienteSeleccionado: Expediente | null;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  onUpdate?: (expediente: Expediente) => void;
  isEditable?: boolean;
  onArchiveSuccess?: () => void;
  setToast: SetToast;
};

/** Combina el expediente básico (listado) con los datos de /stage/full. */
function construirDetalle(
  expediente: Expediente | null,
  full: ExpedienteFullResponse | undefined,
): ExpedienteDetalle | null {
  const info = full?.data;
  if (!expediente || !info) return null;
  const recursoIds = Array.isArray(info.recurso_afectado)
    ? info.recurso_afectado.map((item) => (typeof item === "number" ? item : item?.id))
    : [];
  return {
    id: expediente.id,
    radicado: expediente.radicado,
    expediente: expediente.expediente,
    fecha_creacion: expediente.fecha_creacion,
    municipio: expediente.municipio,
    archivado: expediente.archivado,
    involucrados:
      info.involucrados && info.involucrados.length > 0 ? info.involucrados : expediente.involucrados,
    direccion: info.direccion || expediente.direccion,
    vereda: info.vereda || { id: 0, nombre: "Sin vereda" },
    ultima_etapa: info.ultima_etapa || null,
    recurso_afectado: recursoIds.filter((id): id is number => typeof id === "number"),
    motivo_afectacion: info.motivo_afectacion || "",
  };
}

export default function DetalleExpediente({
  expedienteSeleccionado,
  municipioList,
  recursoAfectadoList,
  setToast,
  onUpdate,
  isEditable = true,
  onArchiveSuccess,
}: Props) {
  const [activeTab, setActiveTab] = useState<string>("info");
  const [isDownloadingAll, setIsDownloadingAll] = useState(false);
  const expedienteActual = expedienteSeleccionado;

  // Al cambiar de expediente en modo consulta se vuelve a "Información".
  const [prevSeleccionado, setPrevSeleccionado] = useState(expedienteSeleccionado);
  if (prevSeleccionado !== expedienteSeleccionado) {
    setPrevSeleccionado(expedienteSeleccionado);
    if (!isEditable) setActiveTab("info");
  }

  const full = useExpedienteFullQuery(expedienteActual?.id);
  const derivado = useMemo(
    () => construirDetalle(expedienteActual, full.data),
    [expedienteActual, full.data],
  );
  // Ediciones locales (datos básicos, última etapa) sobre la respuesta actual.
  const [edicion, setEdicion] = useState<{ base: unknown; detalle: ExpedienteDetalle } | null>(null);
  const expedienteDetalle = edicion && edicion.base === full.data ? edicion.detalle : derivado;

  const etapasExistentes = full.data
    ? (full.data.etapas_existentes ?? [])
    : full.isError
      ? []
      : null;

  const { isError, data: fullData } = full;
  useEffect(() => {
    if (isError) {
      setToast({ id: Date.now(), message: "Error al cargar información completa del expediente", type: "error" });
    } else if (fullData && !fullData.data) {
      setToast({ id: Date.now(), message: "No se encontraron datos adicionales del expediente", type: "error" });
    }
  }, [isError, fullData, setToast]);

  const isEtapaDisponible = (tabId: string): boolean => {
    const tipoEtapaId = ETAPAS_TABS.find((t) => t.id === tabId)?.tipoEtapaId ?? null;
    if (tipoEtapaId === null) return true; // Info siempre disponible
    if (!isEditable) {
      if (etapasExistentes === null) return false; // Cargando: deshabilitar hasta saber
      return etapasExistentes.includes(tipoEtapaId);
    }
    return true; // En modo editable, todas disponibles
  };

  const handleTabClick = (tabId: string) => {
    if (!expedienteDetalle || !isEtapaDisponible(tabId)) return;
    setActiveTab(tabId);
  };

  const handleExpedienteDetalleUpdate = (updated: ExpedienteDetalle) => {
    setEdicion({ base: full.data, detalle: updated });
    // Propagar al padre como Expediente básico
    onUpdate?.({
      id: updated.id,
      radicado: updated.radicado,
      expediente: updated.expediente,
      fecha_creacion: updated.fecha_creacion,
      direccion: updated.direccion,
      municipio: updated.municipio,
      involucrados: updated.involucrados,
      archivado: updated.archivado,
    });
  };

  const handleStageUpdate = (etapa: string) => {
    if (!expedienteDetalle) return;
    setEdicion({ base: full.data, detalle: { ...expedienteDetalle, ultima_etapa: etapa } });
  };

  const handleDownloadAll = async () => {
    if (!expedienteActual) return;
    setIsDownloadingAll(true);
    try {
      const result = await downloadBlobFile(
        API_CONFIG.ENDPOINTS.FILE_DOWNLOAD_ALL(expedienteActual.id),
        `expediente-${expedienteActual.radicado || expedienteActual.id}.pdf`,
      );
      if (!result.ok) {
        if (result.message) setToast({ id: Date.now(), message: result.message, type: "error" });
        return;
      }
      setToast({ id: Date.now(), message: "Descarga iniciada exitosamente", type: "success" });
    } catch {
      setToast({ id: Date.now(), message: "Error al descargar el expediente", type: "error" });
    } finally {
      setIsDownloadingAll(false);
    }
  };

  const renderTabContent = () => {
    if (!expedienteActual) {
      return (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-base-200 rounded-lg border-2 border-dashed border-base-300">
          <div className="w-16 h-16 bg-base-300 rounded-full flex items-center justify-center mb-4">
            <i className="bx bx-folder-open text-2xl text-base-content/60"></i>
          </div>
          <h2 className="text-xl font-medium text-base-content/70 mb-2">
            Sin expediente seleccionado
          </h2>
          <p className="text-base-content/60 max-w-sm">
            Selecciona un expediente para ver {isEditable ? "y gestionar" : ""}{" "}
            sus etapas
          </p>
        </div>
      );
    }

    if (full.isLoading || !expedienteDetalle) {
      return (
        <div className="flex justify-center items-center py-20">
          <div className="flex flex-col items-center gap-4">
            <span className="loading loading-spinner loading-lg text-success"></span>
            <p className="text-base-content/70">Cargando información completa...</p>
          </div>
        </div>
      );
    }

    const currentTab = ETAPAS_TABS.find((tab) => tab.id === activeTab);
    if (!currentTab) return null;
    const Component = currentTab.component;

    // Props comunes para todas las pestañas (cada una toma las que usa).
    const commonProps = {
      expediente: expedienteDetalle,
      radicado: expedienteDetalle.radicado,
      expedienteId: expedienteDetalle.id,
      municipioList,
      recursoAfectadoList,
      tiposNotificacion: full.data?.tipo_notificacion ?? null,
      involucrados: expedienteDetalle.involucrados,
      onExpedienteDetalleUpdate: handleExpedienteDetalleUpdate,
      onStageUpdate: handleStageUpdate,
      setToast,
      isEditable,
      onArchiveSuccess,
    };

    return (
      <ErrorBoundary key={activeTab}>
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
      </ErrorBoundary>
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-base-200">
      {/* HEADER */}
      <div className="flex-shrink-0 bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
                <i className="bx bx-folder-open text-success text-xl"></i>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                  {expedienteActual ? "Expediente Activo" : "Panel"}
                </p>
                <h1 className="text-lg font-bold text-base-content">
                  {expedienteActual ? expedienteActual.radicado : "Panel de Expedientes"}
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

      {/* NAVEGACIÓN DE ETAPAS */}
      {expedienteActual && (
        <EtapasNavegacion
          tabs={ETAPAS_TABS}
          activeTab={activeTab}
          isDisponible={isEtapaDisponible}
          onTabClick={handleTabClick}
        />
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
