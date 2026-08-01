import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import {
  FileText,
  Upload,
  Eye,
  Filter,
  X,
  Plus,
  Search,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { API_CONFIG, apiCall } from "../../../utils/api";
import DocumentoCard from "./DocumentoCard";
import DocumentoDetalleModal from "./DocumentoDetalleModal";
import CrearDocumentoModal from "./CrearDocumentoModal";

type EstadoDocumento = "en_revision" | "aprobado" | "rechazado" | "finalizado";

type DocumentoResumen = {
  id: number;
  nombre: string;
  descripcion?: string;
  estado: EstadoDocumento;
  fecha_creacion: string;
  fecha_ultima_actualizacion: string;
  version_actual: number;
  numero_devoluciones: number;
  usuario_creador_id: number;
  total_revisiones: number;
  total_revisores: number;
};

type Estadisticas = {
  creador?: {
    total_creados: number;
    en_revision: number;
    aprobados: number;
    rechazados: number;
    finalizados: number;
  };
  revisor?: {
    total_asignados: number;
    pendientes: number;
    total_revisiones: number;
    aprobados: number;
    devueltos: number;
  };
};

type Usuario = {
  id: number;
  nombre_completo: string;
  email: string;
};

type Props = {
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
};

const PAGE_SIZE = 20;

export default function DocumentosPage({ setToast }: Props) {
  const location = useLocation();
  const [documentos, setDocumentos] = useState<DocumentoResumen[]>([]);
  const [stats, setStats] = useState<Estadisticas | null>(null);
  const [revisores, setRevisores] = useState<Usuario[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingRevisores, setLoadingRevisores] = useState(true);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showDetalleModal, setShowDetalleModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const [page, setPage] = useState(1);
  const [totalDocs, setTotalDocs] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  const [filtroEstado, setFiltroEstado] = useState<string>("");
  const [filtroFechaDesde, setFiltroFechaDesde] = useState("");
  const [filtroFechaHasta, setFiltroFechaHasta] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  // Abrir modal desde notificación
  useEffect(() => {
    const state = location.state as {
      documentoIdToSelect?: string;
      timestamp?: number;
    } | null;
    if (state?.documentoIdToSelect) {
      const docId = parseInt(state.documentoIdToSelect);
      if (!isNaN(docId)) {
        setSelectedDocId(docId);
        setShowDetalleModal(true);
        window.history.replaceState({}, document.title);
      }
    }
  }, [location]);

  useEffect(() => {
    cargarRevisores();
  }, []);

  useEffect(() => {
    setPage(1);
    cargarDatos(1);
  }, [filtroEstado, filtroFechaDesde, filtroFechaHasta]);

  const cargarRevisores = async () => {
    setLoadingRevisores(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.DOCS_REVIEWERS, {
        method: "GET",
      });
      if (res.ok && Array.isArray(res.usuarios)) {
        setRevisores(res.usuarios);
      } else {
        setRevisores([]);
      }
    } catch {
      setRevisores([]);
    } finally {
      setLoadingRevisores(false);
    }
  };

  const cargarDatos = async (pageNum: number = 1) => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filtroEstado) params.append("estado", filtroEstado);
      if (filtroFechaDesde) params.append("fecha_desde", filtroFechaDesde);
      if (filtroFechaHasta) params.append("fecha_hasta", filtroFechaHasta);
      params.append("page", pageNum.toString());
      params.append("page_size", PAGE_SIZE.toString());

      const endpoint = `${API_CONFIG.ENDPOINTS.DOCS_LIST}?${params.toString()}`;

      const [resDocumentos, resStats] = await Promise.all([
        apiCall(endpoint, { method: "GET" }),
        pageNum === 1
          ? apiCall(API_CONFIG.ENDPOINTS.DOCS_STATS, { method: "GET" })
          : Promise.resolve(null),
      ]);

      if (resDocumentos.ok && Array.isArray(resDocumentos.documentos)) {
        setDocumentos(resDocumentos.documentos);
        setTotalDocs(resDocumentos.total ?? resDocumentos.documentos.length);
        setTotalPages(resDocumentos.total_pages ?? 1);
      } else if (Array.isArray(resDocumentos)) {
        setDocumentos(resDocumentos);
        setTotalDocs(resDocumentos.length);
        setTotalPages(1);
      } else {
        setDocumentos([]);
        setTotalDocs(0);
        setTotalPages(1);
      }

      if (resStats?.ok && resStats?.stats) {
        setStats(resStats.stats);
      }
    } catch {
      setToast({
        id: Date.now(),
        message: "Error al cargar documentos",
        type: "error",
      });
    } finally {
      setLoading(false);
    }
  };

  const cambiarPagina = (newPage: number) => {
    if (newPage < 1 || newPage > totalPages || newPage === page) return;
    setPage(newPage);
    cargarDatos(newPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const limpiarFiltros = () => {
    setFiltroEstado("");
    setFiltroFechaDesde("");
    setFiltroFechaHasta("");
    setSearchTerm("");
  };

  const abrirDetalle = (docId: number) => {
    setSelectedDocId(docId);
    setShowDetalleModal(true);
  };

  const cerrarDetalle = () => {
    setShowDetalleModal(false);
    setSelectedDocId(null);
  };

  const handleDocumentoCreado = () => {
    setPage(1);
    cargarDatos(1);
  };

  const handleDocumentoActualizado = () => {
    cargarDatos(page);
  };

  const documentosFiltrados = documentos.filter((doc) => {
    if (
      searchTerm &&
      !doc.nombre.toLowerCase().includes(searchTerm.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  const tienenFiltrosActivos =
    filtroEstado || filtroFechaDesde || filtroFechaHasta || searchTerm;

  const renderPaginationButtons = () => {
    const buttons: (number | "...")[] = [];
    const delta = 2;
    let prev = 0;

    for (let i = 1; i <= totalPages; i++) {
      if (
        i === 1 ||
        i === totalPages ||
        (i >= page - delta && i <= page + delta)
      ) {
        if (prev && i - prev > 1) buttons.push("...");
        buttons.push(i);
        prev = i;
      }
    }

    return buttons;
  };

  const primerDoc = totalDocs === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const ultimoDoc = Math.min(page * PAGE_SIZE, totalDocs);

  return (
    <div className="min-h-screen bg-base-200">
      {/* Header */}
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm sticky top-0 z-10">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
                <FileText className="text-success" size={20} />
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                  Módulo de Documentos
                </p>
                <h1 className="text-lg font-bold text-base-content">
                  Gestión de Documentos
                </h1>
              </div>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              className="btn btn-success text-white gap-2"
              disabled={loadingRevisores}
            >
              <Plus size={18} />
              Nuevo Documento
            </button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-6 py-6 max-w-7xl">
        <div className="flex gap-6">
          {/* Contenido principal */}
          <div className="flex-1 min-w-0">
            {/* Barra de búsqueda y filtros */}
            <div className="bg-base-100 rounded-lg p-4 shadow-sm border border-base-300 mb-6">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <div className="relative">
                    <Search
                      className="absolute left-3 top-1/2 transform -translate-y-1/2 text-base-content/40"
                      size={18}
                    />
                    <input
                      type="text"
                      placeholder="Buscar por nombre de documento..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="input input-bordered w-full pl-10"
                    />
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => setShowFilters(!showFilters)}
                    className={`btn ${
                      showFilters ? "btn-success" : "btn-ghost"
                    } gap-2`}
                  >
                    <Filter size={18} />
                    Filtros
                    {tienenFiltrosActivos && (
                      <span className="badge badge-success badge-sm">●</span>
                    )}
                  </button>
                  <button
                    onClick={() => cargarDatos(page)}
                    className="btn btn-ghost gap-2"
                    disabled={loading}
                  >
                    <RefreshCw
                      size={18}
                      className={loading ? "animate-spin" : ""}
                    />
                    Actualizar
                  </button>
                </div>
              </div>

              {showFilters && (
                <div className="mt-4 pt-4 border-t border-base-300">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-base-content/70 mb-1">
                        Estado
                      </label>
                      <select
                        value={filtroEstado}
                        onChange={(e) => setFiltroEstado(e.target.value)}
                        className="select select-bordered w-full"
                      >
                        <option value="">Todos los estados</option>
                        <option value="en_revision">En Revisión</option>
                        <option value="aprobado">Aprobado</option>
                        <option value="rechazado">Rechazado</option>
                        <option value="finalizado">Finalizado</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-base-content/70 mb-1">
                        Fecha Desde
                      </label>
                      <input
                        type="date"
                        value={filtroFechaDesde}
                        onChange={(e) => setFiltroFechaDesde(e.target.value)}
                        className="input input-bordered w-full"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-base-content/70 mb-1">
                        Fecha Hasta
                      </label>
                      <input
                        type="date"
                        value={filtroFechaHasta}
                        onChange={(e) => setFiltroFechaHasta(e.target.value)}
                        className="input input-bordered w-full"
                      />
                    </div>
                  </div>

                  {tienenFiltrosActivos && (
                    <div className="mt-4 flex justify-end">
                      <button
                        onClick={limpiarFiltros}
                        className="btn btn-ghost btn-sm gap-2"
                      >
                        <X size={16} />
                        Limpiar Filtros
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Lista de Documentos */}
            {loading ? (
              <div className="flex justify-center items-center py-20">
                <div className="flex flex-col items-center gap-4">
                  <span className="loading loading-spinner loading-lg text-success"></span>
                  <p className="text-base-content/70">Cargando documentos...</p>
                </div>
              </div>
            ) : documentosFiltrados.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 text-center bg-base-100 rounded-lg border-2 border-dashed border-base-300">
                <div className="w-16 h-16 bg-base-300 rounded-full flex items-center justify-center mb-4">
                  <FileText className="text-base-content/40" size={32} />
                </div>
                <h2 className="text-xl font-medium text-base-content/70 mb-2">
                  No hay documentos
                </h2>
                <p className="text-base-content/50 max-w-sm mb-4">
                  {tienenFiltrosActivos
                    ? "No se encontraron documentos con los filtros aplicados"
                    : "Aún no has creado ningún documento"}
                </p>
                {!tienenFiltrosActivos && (
                  <button
                    onClick={() => setShowCreateModal(true)}
                    className="btn btn-success text-white gap-2"
                  >
                    <Plus size={18} />
                    Crear Primer Documento
                  </button>
                )}
              </div>
            ) : (
              <>
                {/* Info de resultados */}
                <div className="flex items-center justify-between mb-3 px-1">
                  <p className="text-sm text-base-content/60">
                    Mostrando {primerDoc}–{ultimoDoc} de {totalDocs} documento
                    {totalDocs !== 1 ? "s" : ""}
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-4">
                  {documentosFiltrados.map((doc, idx) => (
                    <DocumentoCard
                      key={`doc-${doc.id}-${idx}`}
                      documento={doc}
                      onClick={() => abrirDetalle(doc.id)}
                    />
                  ))}
                </div>

                {/* Paginación */}
                {totalPages > 1 && (
                  <div className="flex flex-col items-center gap-2 mt-8">
                    <div className="join">
                      <button
                        className="join-item btn btn-sm"
                        onClick={() => cambiarPagina(page - 1)}
                        disabled={page === 1}
                      >
                        <ChevronLeft size={16} />
                      </button>

                      {renderPaginationButtons().map((p, idx) =>
                        p === "..." ? (
                          <button
                            key={`ellipsis-${idx}`}
                            className="join-item btn btn-sm btn-disabled"
                          >
                            …
                          </button>
                        ) : (
                          <button
                            key={p}
                            className={`join-item btn btn-sm ${
                              p === page ? "btn-success text-white" : ""
                            }`}
                            onClick={() => cambiarPagina(p)}
                          >
                            {p}
                          </button>
                        )
                      )}

                      <button
                        className="join-item btn btn-sm"
                        onClick={() => cambiarPagina(page + 1)}
                        disabled={page === totalPages}
                      >
                        <ChevronRight size={16} />
                      </button>
                    </div>
                    <p className="text-xs text-base-content/50">
                      Página {page} de {totalPages}
                    </p>
                  </div>
                )}
              </>
            )}
          </div>

          {/* Sidebar de Estadísticas */}
          <div className="w-64 flex-shrink-0">
            {stats && (
              <div className="space-y-4 sticky top-24">
                {stats.revisor && (
                  <div className="bg-base-100 rounded-lg p-4 shadow-lg border border-base-300">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="w-8 h-8 bg-info/10 rounded-lg flex items-center justify-center">
                        <Eye className="text-info" size={16} />
                      </div>
                      <h3 className="text-sm font-semibold text-base-content">
                        Revisiones
                      </h3>
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-base-content/70">
                          Asignados
                        </span>
                        <span className="text-lg font-bold text-base-content">
                          {stats.revisor.total_asignados}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-base-content/70">
                          Pendientes
                        </span>
                        <span className="text-lg font-bold text-yellow-600">
                          {stats.revisor.pendientes}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-base-content/70">
                          Aprobados
                        </span>
                        <span className="text-lg font-bold text-green-600">
                          {stats.revisor.aprobados}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-base-content/70">
                          Devueltos
                        </span>
                        <span className="text-lg font-bold text-red-600">
                          {stats.revisor.devueltos}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {stats.creador && (
                  <div className="bg-base-100 rounded-lg p-4 shadow-lg border border-base-300">
                    <div className="flex items-center gap-2 mb-4">
                      <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
                        <Upload className="text-primary" size={16} />
                      </div>
                      <h3 className="text-sm font-semibold text-base-content">
                        Mis Documentos
                      </h3>
                    </div>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-base-content/70">
                          Total Creados
                        </span>
                        <span className="text-lg font-bold text-base-content">
                          {stats.creador.total_creados}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-base-content/70">
                          En Revisión
                        </span>
                        <span className="text-lg font-bold text-yellow-600">
                          {stats.creador.en_revision}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-base-content/70">
                          Aprobados
                        </span>
                        <span className="text-lg font-bold text-green-600">
                          {stats.creador.aprobados}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-base-content/70">
                          Rechazados
                        </span>
                        <span className="text-lg font-bold text-red-600">
                          {stats.creador.rechazados}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {showCreateModal && (
        <CrearDocumentoModal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          onSuccess={handleDocumentoCreado}
          revisores={revisores}
          setToast={setToast}
        />
      )}

      {showDetalleModal && selectedDocId && (
        <DocumentoDetalleModal
          isOpen={showDetalleModal}
          onClose={cerrarDetalle}
          documentoId={selectedDocId}
          onUpdate={handleDocumentoActualizado}
        />
      )}
    </div>
  );
}
