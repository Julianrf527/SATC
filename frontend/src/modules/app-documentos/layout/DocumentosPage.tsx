import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { FileText, Plus } from "lucide-react";
import { ProcesoDetalleModal, usePrecargarProceso } from "@features/proceso-revision";
import { docsAdapter } from "../api/docsAdapter";
import {
  PAGE_SIZE,
  useDocumentosQuery,
  useEstadisticasQuery,
  useInvalidarDocumentos,
  useRevisoresQuery,
} from "../api/documentos";
import type { FiltrosDocumentos, SetToast } from "../types";
import CrearDocumentoModal from "./CrearDocumentoModal";
import DocumentoCard from "./DocumentoCard";
import DocumentosFiltros from "./DocumentosFiltros";
import DocumentosStats from "./DocumentosStats";
import Paginacion from "./Paginacion";

type Props = {
  setToast: SetToast;
};

const FILTROS_VACIOS: FiltrosDocumentos = { estado: "", fechaDesde: "", fechaHasta: "" };

/** Id de documento que manda una notificación (`documentoIdToSelect`). */
function idDesdeNotificacion(state: unknown): number | null {
  const id = Number((state as { documentoIdToSelect?: string } | null)?.documentoIdToSelect);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export default function DocumentosPage({ setToast }: Props) {
  const precargar = usePrecargarProceso(docsAdapter);
  const location = useLocation();
  const [filtros, setFiltrosState] = useState<FiltrosDocumentos>(FILTROS_VACIOS);
  const [page, setPage] = useState(1);
  const [busqueda, setBusqueda] = useState("");
  const [creando, setCreando] = useState(false);
  const [detalleId, setDetalleId] = useState<number | null>(null);

  const lista = useDocumentosQuery(filtros, page);
  const stats = useEstadisticasQuery();
  const revisores = useRevisoresQuery();
  const invalidar = useInvalidarDocumentos();

  // Abrir el documento que manda una notificación (también con la página ya abierta).
  useEffect(() => {
    const id = idDesdeNotificacion(location.state);
    if (id !== null) {
      setDetalleId(id);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  const setFiltros = (f: FiltrosDocumentos) => {
    setFiltrosState(f);
    setPage(1);
  };

  const cambiarPagina = (p: number) => {
    setPage(p);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const datos = lista.data;
  const documentos = (datos?.documentos ?? []).filter(
    (d) => !busqueda || d.nombre.toLowerCase().includes(busqueda.toLowerCase()),
  );
  const total = datos?.total ?? 0;
  const primero = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const ultimo = Math.min(page * PAGE_SIZE, total);
  const hayFiltros = !!(filtros.estado || filtros.fechaDesde || filtros.fechaHasta || busqueda);

  return (
    <div className="min-h-screen bg-base-200">
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
              <FileText className="text-success" size={20} />
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                Módulo de Documentos
              </p>
              <h1 className="text-lg font-bold text-base-content">Gestión de Documentos</h1>
            </div>
          </div>
          <button
            onClick={() => setCreando(true)}
            className="btn btn-success text-white gap-2"
            disabled={revisores.isPending}
          >
            <Plus size={18} />
            Nuevo Documento
          </button>
        </div>
      </div>

      <div className="container mx-auto px-6 py-6 max-w-7xl">
        <div className="flex gap-6">
          <div className="flex-1 min-w-0">
            <DocumentosFiltros
              filtros={filtros}
              estados={lista.data?.estados ?? []}
              onFiltros={setFiltros}
              busqueda={busqueda}
              onBusqueda={setBusqueda}
              onLimpiar={() => {
                setFiltros(FILTROS_VACIOS);
                setBusqueda("");
              }}
              onActualizar={() => invalidar()}
              actualizando={lista.isFetching}
            />

            {lista.isPending ? (
              <div className="flex flex-col items-center gap-4 py-20">
                <span className="loading loading-spinner loading-lg text-success" />
                <p className="text-base-content/70">Cargando documentos...</p>
              </div>
            ) : lista.isError ? (
              <div role="alert" className="alert alert-error">
                Error al cargar documentos
              </div>
            ) : documentos.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center bg-base-100 rounded-lg border-2 border-dashed border-base-300">
                <div className="w-16 h-16 bg-base-300 rounded-full flex items-center justify-center mb-4">
                  <FileText className="text-base-content/60" size={32} />
                </div>
                <h2 className="text-xl font-medium text-base-content/70 mb-2">No hay documentos</h2>
                <p className="text-base-content/60 max-w-sm mb-4">
                  {hayFiltros
                    ? "No se encontraron documentos con los filtros aplicados"
                    : "Aún no has creado ningún documento"}
                </p>
                {!hayFiltros && (
                  <button onClick={() => setCreando(true)} className="btn btn-success text-white gap-2">
                    <Plus size={18} />
                    Crear Primer Documento
                  </button>
                )}
              </div>
            ) : (
              <>
                <p className="text-sm text-base-content/60 mb-3 px-1">
                  Mostrando {primero}–{ultimo} de {total} documento{total !== 1 ? "s" : ""}
                </p>
                <div className="grid grid-cols-1 gap-4">
                  {documentos.map((doc) => (
                    <DocumentoCard
                      key={doc.id}
                      documento={doc}
                      onClick={() => setDetalleId(doc.id)}
                      onPrecargar={() => precargar(doc.id)}
                    />
                  ))}
                </div>
                <Paginacion page={page} totalPages={datos?.total_pages ?? 1} onPage={cambiarPagina} />
              </>
            )}
          </div>

          <aside className="w-64 shrink-0 hidden md:block">
            {stats.data && <DocumentosStats stats={stats.data} />}
          </aside>
        </div>
      </div>

      {creando && (
        <CrearDocumentoModal
          isOpen
          onClose={() => setCreando(false)}
          revisores={revisores.data ?? []}
          setToast={setToast}
        />
      )}

      <ProcesoDetalleModal
        adapter={docsAdapter}
        id={detalleId}
        isOpen={detalleId !== null}
        onClose={() => setDetalleId(null)}
        onCambio={() => invalidar()}
      />
    </div>
  );
}
