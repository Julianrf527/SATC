import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { FileText } from "lucide-react";
import { usePrecargarProceso } from "@features/proceso-revision";
import { useErrorToast } from "@shared/hooks/useErrorToast";
import { documentoAdapter } from "../api/documentoAdapter";
import { FILTROS_MIS_DOCUMENTOS, useMisDocumentosQuery, type FiltrosMisDocumentos } from "../api/misDocumentos";
import { hayFiltrosActivos } from "../api/misDocumentosParams";
import type { MiDocumento, SetToast } from "../types";
import MisDocumentosFiltros from "./mis-informes/MisDocumentosFiltros";
import MisDocumentosTabla from "./mis-informes/MisDocumentosTabla";
import PaginacionMisDocumentos from "./mis-informes/PaginacionMisDocumentos";
import ProcesoDocumentoModal from "./mis-informes/ProcesoDocumentoModal";
import { useIrAlExpediente } from "./mis-informes/useIrAlExpediente";

const SIN_DOCUMENTOS: MiDocumento[] = [];

/** Id del proceso que manda una notificación `recurso_doc`. */
function procesoDesdeNotificacion(state: unknown): number | null {
  const id = Number((state as { procesoIdToSelect?: string } | null)?.procesoIdToSelect);
  return Number.isInteger(id) && id > 0 ? id : null;
}

/**
 * Mis informes (/recurso/my-reports), B.2: como "Mis Informes" de infraction,
 * una sola tabla paginada con todos mis documentos (encargado o revisor, en
 * cualquier estado) y la casilla "Solo los que requieren mi acción". Al abrir
 * una fila se muestra el proceso con `@features/proceso-revision`.
 */
export default function MisInformesRecurso({ setToast }: { setToast: SetToast }) {
  const location = useLocation();
  const precargar = usePrecargarProceso(documentoAdapter);
  const { puedeIr, ir } = useIrAlExpediente();
  const [filtros, setFiltros] = useState(FILTROS_MIS_DOCUMENTOS);
  const [page, setPage] = useState(1);
  const [procesoAbierto, setProcesoAbierto] = useState<number | null>(null);
  const { data, error, isPending, isFetching, isError, refetch } = useMisDocumentosQuery(filtros, page);
  useErrorToast(error, setToast, "Error al cargar tus documentos");

  // Notificación: abre el proceso (el modal lo carga por id; si el usuario
  // no puede verlo el backend responde 403 y el modal lo muestra).
  useEffect(() => {
    const id = procesoDesdeNotificacion(location.state);
    if (id !== null) {
      setProcesoAbierto(id);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  const documentos = data?.data.documentos ?? SIN_DOCUMENTOS;
  const conteos = data?.data.conteos;
  const totalPages = data?.total_pages ?? 1;
  const hayFiltros = hayFiltrosActivos(filtros);

  // Cambiar filtros vuelve a la primera página (como infraction).
  const cambiarFiltros = (f: FiltrosMisDocumentos) => {
    setFiltros(f);
    setPage(1);
  };

  // Si la lista se encoge (p. ej. tras revisar), no quedarse en una página vacía.
  useEffect(() => {
    if (page > totalPages) setPage(totalPages);
  }, [page, totalPages]);

  return (
    <>
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
            <FileText className="text-success" size={20} />
          </div>
          <div>
            <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">Concesiones de Aguas</p>
            <h1 className="text-lg font-bold text-base-content">Mis Informes</h1>
          </div>
        </div>
      </div>

      <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-6xl mx-auto space-y-4">
          <MisDocumentosFiltros
            filtros={filtros}
            onChange={cambiarFiltros}
            opciones={data?.data.filtros}
            onActualizar={() => void refetch()}
            actualizando={isFetching}
          />

          {conteos && conteos.total > 0 && (
            <p className="text-xs text-base-content/60 px-1">
              {conteos.total} {conteos.total === 1 ? "documento" : "documentos"}
              {conteos.requieren_accion > 0 && (
                <>
                  {" · "}
                  <span className="font-semibold text-info">{conteos.requieren_accion} requieren tu acción</span>
                </>
              )}
            </p>
          )}

          <div className="card bg-base-100 shadow border border-base-300">
            <div className="card-body p-0">
              {isPending ? (
                <div className="flex justify-center items-center py-16">
                  <span className="loading loading-spinner loading-lg text-success" />
                </div>
              ) : isError ? (
                <p role="alert" className="text-error text-center py-16">
                  Error al cargar tus documentos
                </p>
              ) : documentos.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <FileText className="w-12 h-12 text-base-content/20 mb-3" />
                  <p className="text-base-content/60">{hayFiltros ? "Sin resultados con los filtros aplicados" : "No tienes documentos asignados"}</p>
                </div>
              ) : (
                <MisDocumentosTabla
                  documentos={documentos}
                  onProceso={(d) => setProcesoAbierto(d.proceso_id)}
                  onPrecargarProceso={(d) => precargar(d.proceso_id)}
                  onExpediente={puedeIr ? ir : undefined}
                />
              )}
              <PaginacionMisDocumentos page={page} totalPages={totalPages} onPage={setPage} deshabilitado={isFetching} />
            </div>
          </div>
        </div>
      </div>

      <ProcesoDocumentoModal procesoId={procesoAbierto} onClose={() => setProcesoAbierto(null)} />
    </>
  );
}
