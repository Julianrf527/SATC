import { lazy, Suspense, useState, type ComponentType, type LazyExoticComponent } from "react";
import ErrorBoundary from "@shared/ui/ErrorBoundary";
import { useErrorToast } from "@shared/hooks/useErrorToast";
import "boxicons/css/boxicons.min.css";
import { descargarExpedienteCompleto, useExpedienteDetalleQuery } from "../api/expedientes";
import type { EtapaProps } from "../etapas/tipos";
import type { CatalogosRecurso, SetToast } from "../types";
import DetalleHeader from "./detalle/DetalleHeader";
import EtapasNav from "./detalle/EtapasNav";
import { ETAPAS_RECURSO, pestanaConDatos, type EtapaTabId } from "./etapasProceso";

// Una pestaña = un componente que recibe EtapaProps.
const COMPONENTES: Record<EtapaTabId, LazyExoticComponent<ComponentType<EtapaProps>>> = {
  info: lazy(() => import("../etapas/informacion-base/InformacionBase")),
  "auto-admite": lazy(() => import("../etapas/auto-admite/AutoAdmite")),
  concepto: lazy(() => import("../etapas/concepto-tecnico/ConceptoTecnico")),
  requerimiento: lazy(() => import("../etapas/requerimiento/Requerimiento")),
  decision: lazy(() => import("../etapas/decision/Decision")),
  memorias: lazy(() => import("../etapas/memorias-calculo/MemoriasCalculo")),
  obras: lazy(() => import("../etapas/recibo-obras/ReciboObras")),
};

type Props = {
  expedienteId: number | null;
  catalogos: CatalogosRecurso;
  setToast: SetToast;
  /** `false` en Consulta: solo lectura + descarga del expediente completo. */
  isEditable: boolean;
  /** Pestaña a abrir (navegación desde Mis informes). */
  pestanaInicial?: EtapaTabId;
};

function Cargando({ texto }: { texto: string }) {
  return (
    <div className="flex justify-center items-center py-20">
      <div className="flex flex-col items-center gap-4">
        <span className="loading loading-spinner loading-lg text-success"></span>
        <p className="text-base-content/70">{texto}</p>
      </div>
    </div>
  );
}

/**
 * Detalle del expediente con navegación de etapas estilo infraction. La
 * fuente de verdad es GET /expedientes/{id}; cada mutación la invalida.
 */
export default function DetalleRecurso({ expedienteId, catalogos, setToast, isEditable, pestanaInicial = "info" }: Props) {
  const [activeTab, setActiveTab] = useState<EtapaTabId>(pestanaInicial);
  const [isTabsCollapsed, setIsTabsCollapsed] = useState(false);
  const [descargando, setDescargando] = useState(false);

  // En consulta, al cambiar de expediente se vuelve a "Información base".
  const [prevId, setPrevId] = useState(expedienteId);
  if (prevId !== expedienteId) {
    setPrevId(expedienteId);
    if (!isEditable) setActiveTab("info");
  }

  const query = useExpedienteDetalleQuery(expedienteId);
  useErrorToast(query.error, setToast, "Error al cargar la información del expediente");
  const expediente = query.data ?? null;

  // En Consulta se deshabilitan las pestañas de etapas que no existen.
  const isDisponible = (id: string) => isEditable || pestanaConDatos(id as EtapaTabId, expediente?.etapas);

  const handleDescargar = async () => {
    if (!expediente) return;
    setDescargando(true);
    try {
      const res = await descargarExpedienteCompleto(expediente.id, expediente.expediente);
      setToast(
        res.ok
          ? { id: Date.now(), message: "Descarga iniciada exitosamente", type: "success" }
          : { id: Date.now(), message: res.message ?? "No se pudo descargar el expediente", type: "error" },
      );
    } catch {
      setToast({ id: Date.now(), message: "Error al descargar el expediente", type: "error" });
    } finally {
      setDescargando(false);
    }
  };

  const contenido = () => {
    if (!expedienteId) {
      return (
        <div className="flex flex-col items-center justify-center py-20 text-center bg-base-200 rounded-lg border-2 border-dashed border-base-300">
          <div className="w-16 h-16 bg-base-300 rounded-full flex items-center justify-center mb-4">
            <i className="bx bx-folder-open text-2xl text-base-content/60"></i>
          </div>
          <h2 className="text-xl font-medium text-base-content/70 mb-2">Sin expediente seleccionado</h2>
          <p className="text-base-content/60 max-w-sm">
            Selecciona un expediente para ver {isEditable ? "y gestionar " : ""}sus etapas
          </p>
        </div>
      );
    }
    if (query.isPending) return <Cargando texto="Cargando información completa..." />;
    if (!expediente) {
      return (
        <p role="alert" className="text-error text-center py-16">
          No se pudo cargar el expediente
        </p>
      );
    }
    const Componente = COMPONENTES[activeTab];
    return (
      <ErrorBoundary key={activeTab}>
        <Suspense fallback={<Cargando texto="Cargando contenido..." />}>
          <Componente
            expediente={expediente}
            etapas={expediente.etapas}
            catalogos={catalogos}
            setToast={setToast}
            isEditable={isEditable}
          />
        </Suspense>
      </ErrorBoundary>
    );
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-base-200">
      <DetalleHeader
        titulo={expediente?.expediente ?? null}
        subtitulo={expediente?.radicado}
        modoConsulta={!isEditable}
        mostrarDescarga={!isEditable && !!expediente?.acciones_disponibles.includes("descargar_expediente")}
        isDownloading={descargando}
        onDownload={handleDescargar}
      />

      {expedienteId && (
        <EtapasNav
          tabs={ETAPAS_RECURSO}
          activeTab={activeTab}
          isDisponible={isDisponible}
          onTabClick={(id) => setActiveTab(id as EtapaTabId)}
          isCollapsed={isTabsCollapsed}
          setIsCollapsed={setIsTabsCollapsed}
        />
      )}

      <div className="flex-1 overflow-y-auto bg-base-200">
        <div className="container mx-auto p-6 max-w-7xl">
          <div className="bg-base-100 rounded-lg shadow-sm border border-base-300">
            <div className="p-8">{contenido()}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
