import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  Eye,
  Leaf,
  ExternalLink,
  CheckCircle,
  Clock,
  AlertCircle,
  Download,
  Filter,
  RefreshCw,
  X,
} from "lucide-react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import type { MiInforme } from "../../../types/infraccionApp";
import { openDocumentById } from "../../../utils/documentViewer";
import DocumentoDetalleModal from "../../app-documentos/layout/DocumentoDetalleModal";
import MatrizRecursosAfectadosModal from "../Modal/MatrizRecursosAfectadosModal";
import CustomSelect from "../../Common/Form/CustomSelect";

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

const formatDate = (d: string | null) => {
  if (!d) return "—";
  const [year, month, day] = d.split("T")[0].split("-");
  return `${day}/${month}/${year}`;
};

const EstadoBadge = ({ informe }: { informe: MiInforme }) => {
  if (informe.aceptado) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold text-success bg-success/10 px-2 py-0.5 rounded-full">
        <CheckCircle size={12} /> Aceptado
      </span>
    );
  }
  if (informe.proceso_activo) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold text-warning bg-warning/10 px-2 py-0.5 rounded-full">
        <Clock size={12} /> En proceso
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-semibold text-base-content/50 bg-base-200 px-2 py-0.5 rounded-full">
      <AlertCircle size={12} /> Sin proceso
    </span>
  );
};

export default function MisInformes({ setToast }: Props) {
  const navigate = useNavigate();
  const [informes, setInformes] = useState<MiInforme[]>([]);
  const [loading, setLoading] = useState(true);

  const [radicadoFilter, setRadicadoFilter] = useState("");
  const [tipoFilter, setTipoFilter] = useState("all");
  const [rolFilter, setRolFilter] = useState("all");
  const [estadoFilter, setEstadoFilter] = useState("all");

  const [docsModal, setDocsModal] = useState<{
    open: boolean;
    docsDocumentoId: number | null;
  }>({ open: false, docsDocumentoId: null });

  const [matrizModal, setMatrizModal] = useState<{
    open: boolean;
    informeId: number | null;
  }>({ open: false, informeId: null });

  const loadInformes = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.INFRACTION_MIS_INFORMES, { method: "GET" });
      if (res.ok) {
        setInformes(res.data || []);
      } else {
        setToast({ id: Date.now(), message: res.detail || "Error al cargar tus informes", type: "error" });
      }
    } catch {
      setToast({ id: Date.now(), message: "Error de conexión", type: "error" });
    } finally {
      setLoading(false);
    }
  }, [setToast]);

  useEffect(() => {
    loadInformes();
  }, [loadInformes]);

  const goToExpediente = (informe: MiInforme) => {
    navigate("/infraction/consult", {
      state: { radicadoToSelect: informe.expediente_radicado, timestamp: Date.now() },
    });
  };

  const clearFilters = () => {
    setRadicadoFilter("");
    setTipoFilter("all");
    setRolFilter("all");
    setEstadoFilter("all");
  };

  const hasActiveFilters =
    radicadoFilter !== "" || tipoFilter !== "all" || rolFilter !== "all" || estadoFilter !== "all";

  const informesFiltrados = useMemo(
    () =>
      informes.filter((inf) => {
        const matchesRadicado = radicadoFilter
          ? (inf.expediente_radicado ?? "").toLowerCase().includes(radicadoFilter.toLowerCase())
          : true;
        const matchesTipo = tipoFilter === "all" ? true : inf.tipo_informe === tipoFilter;
        const matchesRol =
          rolFilter === "all"
            ? true
            : rolFilter === "profesional"
              ? inf.soy_profesional
              : inf.soy_revisor;
        const matchesEstado =
          estadoFilter === "all"
            ? true
            : estadoFilter === "aceptado"
              ? inf.aceptado
              : estadoFilter === "en_proceso"
                ? !inf.aceptado && inf.proceso_activo
                : !inf.aceptado && !inf.proceso_activo;
        return matchesRadicado && matchesTipo && matchesRol && matchesEstado;
      }),
    [informes, radicadoFilter, tipoFilter, rolFilter, estadoFilter],
  );

  return (
    <>
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
              <FileText className="text-success" size={20} />
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">
                Módulo de Infracciones
              </p>
              <h1 className="text-lg font-bold text-base-content">Mis Informes</h1>
            </div>
          </div>
        </div>
      </div>

      <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-6xl mx-auto space-y-4">
          <div className="card bg-base-100 shadow border border-base-300">
            <div className="card-body p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold text-base-content/70 flex items-center gap-2">
                  <Filter size={14} />
                  Filtros de búsqueda
                  {hasActiveFilters && <span className="badge badge-success badge-sm">activos</span>}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={loadInformes}
                    className="btn btn-ghost btn-xs gap-1"
                    disabled={loading}
                  >
                    <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
                    Actualizar
                  </button>
                  <button
                    onClick={clearFilters}
                    disabled={!hasActiveFilters}
                    className={`btn btn-xs gap-1 ${hasActiveFilters ? "btn-error btn-outline" : "btn-ghost opacity-40"}`}
                  >
                    <X size={12} />
                    Limpiar
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Radicado</span>
                  <input
                    type="text"
                    placeholder="Buscar..."
                    className="input input-sm input-bordered w-full"
                    value={radicadoFilter}
                    onChange={(e) => setRadicadoFilter(e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Tipo informe</span>
                  <CustomSelect
                    className="select-sm"
                    value={tipoFilter}
                    onChange={setTipoFilter}
                    hidePlaceholderOption
                    options={[
                      { value: "all", label: "Todos" },
                      { value: "VISITA", label: "VISITA" },
                      { value: "SEGUIMIENTO", label: "SEGUIMIENTO" },
                    ]}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Mi rol</span>
                  <CustomSelect
                    className="select-sm"
                    value={rolFilter}
                    onChange={setRolFilter}
                    hidePlaceholderOption
                    options={[
                      { value: "all", label: "Todos" },
                      { value: "profesional", label: "Profesional" },
                      { value: "revisor", label: "Revisor" },
                    ]}
                  />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-xs font-medium text-base-content/60">Estado</span>
                  <CustomSelect
                    className="select-sm"
                    value={estadoFilter}
                    onChange={setEstadoFilter}
                    hidePlaceholderOption
                    options={[
                      { value: "all", label: "Todos" },
                      { value: "aceptado", label: "Aceptado" },
                      { value: "en_proceso", label: "En proceso" },
                      { value: "sin_proceso", label: "Sin proceso" },
                    ]}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="card bg-base-100 shadow border border-base-300">
            <div className="card-body p-0">
              {loading ? (
                <div className="flex justify-center items-center py-16">
                  <span className="loading loading-spinner loading-lg text-success" />
                </div>
              ) : informesFiltrados.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <FileText className="w-12 h-12 text-base-content/20 mb-3" />
                  <p className="text-base-content/50">
                    {hasActiveFilters ? "Sin resultados con los filtros aplicados" : "No tienes informes técnicos asignados"}
                  </p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="table table-sm w-full">
                    <thead className="bg-base-200">
                      <tr>
                        <th className="text-xs">Expediente</th>
                        <th className="text-xs">Tipo</th>
                        <th className="text-xs">Rol</th>
                        <th className="text-xs">Modo</th>
                        <th className="text-xs">Fecha Aceptación</th>
                        <th className="text-xs">Estado</th>
                        <th className="text-xs text-center">Acciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {informesFiltrados.map((inf) => (
                        <tr key={inf.id} className="hover:bg-base-50 border-b border-base-200">
                          <td className="font-mono text-xs font-semibold">
                            <button
                              onClick={() => goToExpediente(inf)}
                              className="btn btn-ghost btn-xs gap-1 text-primary"
                            >
                              {inf.expediente_radicado ?? `#${inf.expediente_id}`}
                              <ExternalLink size={10} />
                            </button>
                          </td>
                          <td>
                            <span className={`badge badge-sm ${inf.tipo_informe === "VISITA" ? "badge-info" : "badge-secondary"}`}>
                              {inf.tipo_informe}
                            </span>
                          </td>
                          <td className="text-xs">
                            <div className="flex gap-1">
                              {inf.soy_profesional && <span className="badge badge-ghost badge-xs">Profesional</span>}
                              {inf.soy_revisor && <span className="badge badge-ghost badge-xs">Revisor</span>}
                            </div>
                          </td>
                          <td className="text-xs">{inf.modo === "MANUAL" ? "Manual" : "Flujo"}</td>
                          <td className="text-xs">{formatDate(inf.fecha_aceptacion_informe)}</td>
                          <td>
                            <EstadoBadge informe={inf} />
                          </td>
                          <td>
                            <div className="flex items-center justify-center gap-1">
                              {inf.aceptado && inf.documento_informe_id && (
                                <button
                                  onClick={() => openDocumentById(inf.documento_informe_id!)}
                                  className="btn btn-ghost btn-xs gap-1 text-success"
                                  title="Ver documento aceptado"
                                >
                                  <Download size={13} />
                                  Ver doc
                                </button>
                              )}
                              {inf.proceso_activo && inf.docs_documento_id && (
                                <button
                                  onClick={() =>
                                    setDocsModal({ open: true, docsDocumentoId: inf.docs_documento_id })
                                  }
                                  className="btn btn-ghost btn-xs gap-1 text-info"
                                >
                                  <Eye size={13} />
                                  Proceso
                                </button>
                              )}
                              {inf.puede_diligenciar_matriz && (
                                <button
                                  onClick={() => setMatrizModal({ open: true, informeId: inf.id })}
                                  className="btn btn-ghost btn-xs gap-1 text-success"
                                >
                                  <Leaf size={13} />
                                  {inf.tiene_matriz ? "Editar matriz" : "Matriz"}
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {docsModal.open && docsModal.docsDocumentoId && (
        <DocumentoDetalleModal
          isOpen={docsModal.open}
          onClose={() => setDocsModal({ open: false, docsDocumentoId: null })}
          documentoId={docsModal.docsDocumentoId}
          setToast={setToast}
          onUpdate={(accion) => {
            if (accion === "revision" && docsModal.docsDocumentoId) {
              apiCall(API_CONFIG.ENDPOINTS.INFRACTION_REPORTS_SYNC_BY_DOC(docsModal.docsDocumentoId), {
                method: "PUT",
              }).catch(() => {});
            }
            loadInformes();
          }}
        />
      )}

      {matrizModal.open && matrizModal.informeId && (
        <MatrizRecursosAfectadosModal
          isOpen={matrizModal.open}
          onClose={() => {
            setMatrizModal({ open: false, informeId: null });
            loadInformes();
          }}
          informeId={matrizModal.informeId}
          setToast={setToast}
        />
      )}
    </>
  );
}
