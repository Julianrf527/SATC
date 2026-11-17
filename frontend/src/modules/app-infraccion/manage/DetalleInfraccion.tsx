import { useState, useEffect, useMemo, lazy, Suspense, type ComponentType, type LazyExoticComponent } from "react";
import { API_CONFIG } from "@shared/lib/api";
import { downloadBlobFile } from "@shared/lib/downloadFile";
import ErrorBoundary from "@shared/ui/ErrorBoundary";
import "boxicons/css/boxicons.min.css";
import type {
  Expediente,
  ExpedienteCompletoResponse,
  ExpedienteDetalle,
  Quejoso,
  TipoAfectacion,
} from "../types";
import type { Municipio, ModeloGenerico } from "@shared/types/common";
import { useExpedienteCompletoQuery } from "../api/expediente";
import DetalleHeader from "./detalle-infraccion/DetalleHeader";
import EtapasNav, { type EtapaTabInfo } from "./detalle-infraccion/EtapasNav";
import { ETIQUETA_ETAPA } from "./etapasProceso";

const InformacionExpediente = lazy(
  () => import("../etapas/InformacionInfraccion"),
);
const Respuesta = lazy(() => import("../etapas/Respuesta"));
const Visita = lazy(() => import("../etapas/Visita"));
const Concepto = lazy(() => import("../etapas/Concepto"));
const Seguimiento = lazy(() => import("../etapas/Seguimiento"));
const Cierre = lazy(() => import("../etapas/Cierre"));

type SetToast = (toast: {
  id: number;
  message: string;
  type: "success" | "error";
}) => void;

/** Props que reciben todas las pestañas (cada una usa el subconjunto que necesita). */
type EtapaProps = {
  expediente: ExpedienteDetalle;
  expedienteId: number;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  tipoAfectacionList: TipoAfectacion[];
  quejosoList: Quejoso[];
  setQuejosoList?: (quejosos: Quejoso[]) => void;
  tiposNotificacion: ModeloGenerico | null;
  involucrados: ExpedienteDetalle["involucrados"];
  setToast: SetToast;
  isEditable: boolean;
  onArchiveSuccess?: () => void;
};

type Tab = EtapaTabInfo & {
  component: LazyExoticComponent<ComponentType<EtapaProps>>;
};

const TABS: Tab[] = [
  { id: "info", label: "Información", icon: "bx-info-circle", component: InformacionExpediente },
  { id: "respuesta", label: ETIQUETA_ETAPA.respuesta, icon: "bx-search-alt", component: Respuesta },
  { id: "visita", label: ETIQUETA_ETAPA.visita, icon: "bx-error-alt", component: Visita },
  { id: "concepto", label: ETIQUETA_ETAPA.concepto, icon: "bx-book-bookmark", component: Concepto },
  { id: "seguimiento", label: ETIQUETA_ETAPA.seguimiento, icon: "bx-error-alt", component: Seguimiento },
  { id: "cierre", label: ETIQUETA_ETAPA.cierre, icon: "bx-check-circle", component: Cierre },
];

// tab.id (= código de etapa del backend) -> tipo_etapa_id / orden del proceso
// (Información siempre visible)
const TAB_TO_ETAPA: Record<string, number | null> = {
  info: null,
  respuesta: 1,
  visita: 2,
  concepto: 3,
  seguimiento: 4,
  cierre: 5,
};

/**
 * Detalle del expediente: la fuente de verdad es /expedientes/completo (última
 * etapa y estado los calcula el backend y se refrescan al invalidar la
 * consulta tras cada mutación). Del expediente de la lista solo se toma lo que
 * /completo no trae si viniera vacío.
 */
function construirDetalle(
  base: Expediente,
  response: ExpedienteCompletoResponse | undefined,
): ExpedienteDetalle | null {
  const information = response?.data;
  if (!information) return null;
  return {
    id: base.id,
    radicado: information.radicado ?? base.radicado,
    fecha_radicado: information.fecha_radicado ?? base.fecha_radicado,
    municipio: information.municipio ?? base.municipio,
    fecha_creacion: information.fecha_creacion ?? base.fecha_creacion,
    archivado: information.archivado ?? base.archivado,
    etapa_actual: information.etapa_actual ?? information.ultima_etapa ?? null,
    estado: information.estado ?? null,
    direccion: information.direccion || "",
    descripcion: information.descripcion || "",
    vereda: information.vereda || { id: 0, nombre: "Sin vereda" },
    quejosos: information.quejosos || [],
    tipos_afectacion: information.tipos_afectacion || [],
    recurso_afectado: information.recurso_afectado || [],
    radicados_asociados: information.radicados_asociados || [],
    radicado_inicial: information.radicado_inicial ?? null,
    involucrados: information.involucrados ?? base.involucrados ?? [],
  };
}

type Props = {
  expedienteSeleccionado: Expediente | null;
  municipioList: Municipio[];
  setToast: SetToast;
  recursoAfectadoList: ModeloGenerico[];
  tipoAfectacionList: TipoAfectacion[];
  quejosoList: Quejoso[];
  setQuejosoList?: (quejosos: Quejoso[]) => void;
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
  isEditable = true,
  onArchiveSuccess,
}: Props) {
  const expedienteActual = expedienteSeleccionado;
  const [activeTab, setActiveTab] = useState<string>("info");
  const [isTabsCollapsed, setIsTabsCollapsed] = useState(false);
  const [isDownloadingAll, setIsDownloadingAll] = useState(false);

  // En modo consulta, al cambiar de expediente se vuelve a "Información".
  const [prevSeleccionado, setPrevSeleccionado] = useState(expedienteSeleccionado);
  if (prevSeleccionado !== expedienteSeleccionado) {
    setPrevSeleccionado(expedienteSeleccionado);
    if (!isEditable) setActiveTab("info");
  }

  const query = useExpedienteCompletoQuery(expedienteActual?.id);

  useEffect(() => {
    if (query.isError) {
      setToast({ id: Date.now(), message: "Error al cargar información completa del expediente", type: "error" });
    } else if (query.isSuccess && !query.data?.data) {
      setToast({ id: Date.now(), message: "No se encontraron datos adicionales del expediente", type: "error" });
    }
    // Solo al cambiar el resultado de la consulta.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query.isError, query.isSuccess, query.data]);

  const expedienteDetalle = useMemo(
    () => (expedienteActual ? construirDetalle(expedienteActual, query.data) : null),
    [expedienteActual, query.data],
  );

  const tipoNotificacion = query.data?.tipo_notificacion ?? null;
  const etapasExistentes: number[] | null = query.isError
    ? []
    : query.data
      ? (query.data.etapas_existentes ?? [])
      : null;

  const isEtapaDisponible = (tabId: string): boolean => {
    const etapaId = TAB_TO_ETAPA[tabId];
    if (etapaId === null) return true; // Info siempre disponible
    if (!isEditable) {
      if (etapasExistentes === null) return false; // Cargando: deshabilitar hasta saber
      return etapasExistentes.includes(etapaId);
    }
    return true; // En modo editable, todas disponibles
  };

  const handleTabClick = (tabId: string) => {
    if (!expedienteActual || !isEtapaDisponible(tabId)) return;
    setActiveTab(tabId);
  };

  const handleDownloadAll = async () => {
    if (!expedienteDetalle) return;
    setIsDownloadingAll(true);
    try {
      const endpoint = API_CONFIG.ENDPOINTS.INFRACTION_DOWNLOAD_ALL(expedienteDetalle.id);
      const filename = `expediente-${expedienteDetalle.radicado || expedienteDetalle.id}.pdf`;
      const result = await downloadBlobFile(endpoint, filename);
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
    if (query.isPending && expedienteActual) {
      return (
        <div className="flex justify-center items-center py-20">
          <div className="flex flex-col items-center gap-4">
            <span className="loading loading-spinner loading-lg text-success"></span>
            <p className="text-base-content/70">Cargando información completa...</p>
          </div>
        </div>
      );
    }

    if (!expedienteDetalle) {
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

    const currentTab = TABS.find((tab) => tab.id === activeTab);
    if (!currentTab) return null;
    const Component = currentTab.component;

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
          <Component
            expediente={expedienteDetalle}
            expedienteId={expedienteDetalle.id}
            municipioList={municipioList}
            recursoAfectadoList={recursoAfectadoList}
            tipoAfectacionList={tipoAfectacionList}
            quejosoList={quejosoList}
            setQuejosoList={setQuejosoList}
            tiposNotificacion={tipoNotificacion}
            involucrados={expedienteDetalle.involucrados}
            setToast={setToast}
            isEditable={isEditable}
            onArchiveSuccess={onArchiveSuccess}
          />
        </Suspense>
      </ErrorBoundary>
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-base-200">
      <DetalleHeader
        radicado={expedienteDetalle?.radicado ?? expedienteActual?.radicado ?? null}
        mostrarDescarga={!isEditable && !!expedienteActual}
        isDownloading={isDownloadingAll}
        onDownload={handleDownloadAll}
      />

      {expedienteActual && (
        <EtapasNav
          tabs={TABS}
          activeTab={activeTab}
          isDisponible={isEtapaDisponible}
          onTabClick={handleTabClick}
          isCollapsed={isTabsCollapsed}
          setIsCollapsed={setIsTabsCollapsed}
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
