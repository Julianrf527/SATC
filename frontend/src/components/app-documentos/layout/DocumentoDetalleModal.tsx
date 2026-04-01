import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { API_CONFIG, apiCall, BASE_URL } from "../../../utils/api";
import { useAuth } from "../../../context/AuthContext";
import {
  X,
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Download,
  Eye,
  Upload,
  Users,
  Calendar,
  ChevronRight,
} from "lucide-react";
import SubirVersionModal from "./SubirVersionModal";
import RevisarDocumentoModal from "./RevisarDocumentoModal";

type EstadoDocumento = "en_revision" | "aprobado" | "rechazado" | "finalizado";

type Version = {
  version_id: number;
  numero_version: number;
  archivo_url: string;
  archivo_nombre: string;
  archivo_size: number;
  fecha_subida: string;
  comentario?: string;
};

type Revision = {
  revision_id: number;
  revisor_id: number;
  estado: string;
  comentarios?: string;
  fecha_revision: string;
  version_revisada: number;
};

type RevisorAsignado = {
  revisor_id: number;
  fecha_asignacion: string;
  notificado: boolean;
};

type AuditoriaItem = {
  auditoria_id: number;
  usuario_id: number;
  accion: string;
  descripcion?: string;
  fecha_accion: string;
};

type DocumentoCompleto = {
  documento_id: number;
  nombre: string;
  descripcion?: string;
  tipo_archivo: string;
  estado: EstadoDocumento;
  version_actual: number;
  numero_devoluciones: number;
  fecha_creacion: string;
  usuario_creador_id: number;
  versiones: Version[];
  revisiones: Revision[];
  revisores_asignados: RevisorAsignado[];
  auditoria: AuditoriaItem[];
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  documentoId: number;
  onUpdate: () => void;
};

const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("es-CO", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
};

const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
};

export default function DocumentoDetalleModal({
  isOpen,
  onClose,
  documentoId,
  onUpdate,
}: Props) {
  const [documento, setDocumento] = useState<DocumentoCompleto | null>(null);
  const [loading, setLoading] = useState(true);
  const [theme, setTheme] = useState<string>("emerald");
  const [showSubirVersionModal, setShowSubirVersionModal] = useState(false);
  const [showRevisarModal, setShowRevisarModal] = useState(false);

  // Obtener usuario actual del contexto
  const { user } = useAuth();
  const usuarioActualId = user?.user_id || 0;

  // Detectar tema
  useEffect(() => {
    const updateTheme = () => {
      const currentTheme =
        document.querySelector("[data-theme]")?.getAttribute("data-theme") ||
        "emerald";
      setTheme(currentTheme);
    };

    updateTheme();

    const observer = new MutationObserver(updateTheme);
    const targetNode = document.querySelector("[data-theme]");

    if (targetNode) {
      observer.observe(targetNode, {
        attributes: true,
        attributeFilter: ["data-theme"],
      });
    }

    return () => observer.disconnect();
  }, []);

  // Cargar documento completo
  useEffect(() => {
    if (isOpen && documentoId) {
      cargarDocumento();
    }
  }, [isOpen, documentoId]);

  const cargarDocumento = async () => {
    setLoading(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.DOCS_DETAIL(documentoId), {
        method: "GET",
      });

      if (res.ok) {
        setDocumento(res);
      }
    } catch (error) {
      /* console.error("Error cargando documento:", error); */
    } finally {
      setLoading(false);
    }
  };

  const handleDescargarArchivo = async (
    versionId: number,
    archivo_nombre: string,
    tipo_archivo: string,
  ) => {
    try {
      const url = `${BASE_URL}${API_CONFIG.ENDPOINTS.DOCS_DOWNLOAD(versionId)}`;

      // Si es PDF, abrir en nueva pestaña
      if (tipo_archivo === "pdf") {
        window.open(url, "_blank");
      } else {
        // Si es Word, descargar directamente
        const link = document.createElement("a");
        link.href = url;
        link.download = archivo_nombre;
        link.click();
      }
    } catch (error) {
      /* console.error("Error descargando archivo:", error); */
    }
  };

  const handleVersionSubida = () => {
    cargarDocumento();
    onUpdate();
  };

  const handleRevisionRealizada = () => {
    cargarDocumento();
    onUpdate();
  };

  const getEstadoBadge = (estado: EstadoDocumento) => {
    const badges = {
      en_revision: {
        color: "bg-yellow-500/20 text-yellow-700 border-yellow-500/30",
        icon: Clock,
        text: "En Revisión",
      },
      aprobado: {
        color: "bg-green-500/20 text-green-700 border-green-500/30",
        icon: CheckCircle,
        text: "Aprobado",
      },
      rechazado: {
        color: "bg-red-500/20 text-red-700 border-red-500/30",
        icon: XCircle,
        text: "Rechazado",
      },
      finalizado: {
        color: "bg-gray-500/20 text-gray-700 border-gray-500/30",
        icon: AlertCircle,
        text: "Finalizado",
      },
    };

    const badge = badges[estado];
    const Icon = badge.icon;

    return (
      <span
        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border ${badge.color}`}
      >
        <Icon className="w-3.5 h-3.5" />
        {badge.text}
      </span>
    );
  };

  const getAccionTexto = (accion: string) => {
    switch (accion) {
      case "crear":
        return "Creado";
      case "subir_version":
        return "Nueva Versión";
      case "devolver":
        return "Devuelto";
      case "aprobar":
        return "Aprobado";
      case "actualizar":
        return "Actualizado";
      case "finalizar":
        return "Finalizado";
      default:
        return accion.replace("_", " ");
    }
  };

  const getAccionIcon = (accion: string) => {
    switch (accion) {
      case "crear":
        return <Upload className="text-yellow-500" size={16} />;
      case "subir_version":
        return <Upload className="text-blue-500" size={16} />;
      case "devolver":
        return <XCircle className="text-red-500" size={16} />;
      case "aprobar":
        return <CheckCircle className="text-green-500" size={16} />;
      case "actualizar":
        return <Clock className="text-purple-500" size={16} />;
      case "finalizar":
        return <AlertCircle className="text-gray-500" size={16} />;
      default:
        return <Clock className="text-blue-500" size={16} />;
    }
  };

  const getAccionBorderColor = (accion: string) => {
    switch (accion) {
      case "crear":
        return "border-yellow-500";
      case "subir_version":
        return "border-blue-500";
      case "devolver":
        return "border-red-500";
      case "aprobar":
        return "border-green-500";
      case "actualizar":
        return "border-purple-500";
      case "finalizar":
        return "border-gray-500";
      default:
        return "border-success";
    }
  };

  // Determinar permisos y acciones disponibles
  const esCreador =
    Number(documento?.usuario_creador_id) === Number(usuarioActualId);
  const esRevisor = documento?.revisores_asignados.some(
    (r) => Number(r.revisor_id) === Number(usuarioActualId),
  );
  const puedeSubirVersion = esCreador && documento?.estado === "rechazado";

  // Verificar si ya revisó la versión actual
  const yaRevisoVersionActual = documento?.revisiones.some(
    (r) =>
      Number(r.revisor_id) === Number(usuarioActualId) &&
      r.version_revisada === documento.version_actual,
  );

  const puedeRevisar =
    esRevisor && documento?.estado === "en_revision" && !yaRevisoVersionActual;

  const handleClose = () => {
    setDocumento(null);
    onClose();
  };

  if (!isOpen) return null;

  const modalContent = (
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleClose}
    >
      <div
        className="bg-base-100 rounded-lg w-full max-w-6xl mx-4 shadow-2xl max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-base-100 border-b border-base-300 px-6 py-4 flex items-center justify-between z-10">
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <FileText className="text-success" size={20} />
            </div>
            <div className="flex-1 min-w-0">
              {loading ? (
                <div className="h-6 w-64 bg-base-300 animate-pulse rounded"></div>
              ) : (
                <>
                  <h3 className="font-bold text-lg text-base-content truncate">
                    {documento?.nombre}
                  </h3>
                  <p className="text-xs text-base-content/60">
                    Versión {documento?.version_actual} •{" "}
                    {documento?.tipo_archivo.toUpperCase()}
                  </p>
                </>
              )}
            </div>
          </div>
          <button
            onClick={handleClose}
            className="btn btn-ghost btn-sm btn-circle flex-shrink-0"
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        {loading ? (
          <div className="flex justify-center items-center py-20">
            <div className="flex flex-col items-center gap-4">
              <span className="loading loading-spinner loading-lg text-success"></span>
              <p className="text-base-content/70">Cargando información...</p>
            </div>
          </div>
        ) : documento ? (
          <div className="p-6 space-y-6">
            {/* Info general y estado */}
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                {documento.descripcion && (
                  <p className="text-base-content/70 mb-3">
                    {documento.descripcion}
                  </p>
                )}
                <div className="flex flex-wrap gap-3 text-sm text-base-content/60">
                  <div className="flex items-center gap-2">
                    <Calendar size={14} />
                    <span>Creado: {formatDate(documento.fecha_creacion)}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Users size={14} />
                    <span>
                      {documento.revisores_asignados.length} Revisor(es)
                    </span>
                  </div>
                  {documento.numero_devoluciones > 0 && (
                    <div className="flex items-center gap-2 text-red-600 font-semibold">
                      <XCircle size={14} />
                      <span>
                        {documento.numero_devoluciones}/3 Devoluciones
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap items-center justify-end gap-2">
                {getEstadoBadge(documento.estado)}
                {puedeSubirVersion && (
                  <button
                    onClick={() => setShowSubirVersionModal(true)}
                    className="btn btn-sm btn-primary gap-2"
                  >
                    <Upload size={16} />
                    Subir Nueva Versión
                  </button>
                )}
                {puedeRevisar && (
                  <button
                    onClick={() => setShowRevisarModal(true)}
                    className="btn btn-sm btn-success text-white gap-2"
                  >
                    <Eye size={16} />
                    Revisar Documento
                  </button>
                )}
              </div>
            </div>

            {/* Timeline Horizontal de Auditoría */}
            <div className="bg-base-200 rounded-lg p-5">
              <h4 className="font-semibold text-base-content mb-4 flex items-center gap-2">
                <Clock size={18} />
                Historial del Documento
              </h4>

              <div className="relative">
                {/* Línea horizontal */}
                <div className="absolute top-8 left-0 right-0 h-0.5 bg-base-300"></div>

                {/* Eventos */}
                <div className="relative flex overflow-x-auto pb-4 gap-8">
                  {documento.auditoria.map((item, index) => (
                    <div key={item.auditoria_id} className="flex-shrink-0 w-48">
                      <div className="flex flex-col items-center">
                        {/* Punto en la línea */}
                        <div
                          className={`w-16 h-16 bg-base-100 border-2 ${getAccionBorderColor(
                            item.accion,
                          )} rounded-full flex items-center justify-center shadow-lg z-10 mb-3`}
                        >
                          {getAccionIcon(item.accion)}
                        </div>

                        {/* Información del evento */}
                        <div className="text-center">
                          <p className="font-semibold text-sm text-base-content mb-1">
                            {getAccionTexto(item.accion)}
                          </p>
                          <p className="text-xs text-base-content/60 mb-1">
                            {formatDate(item.fecha_accion)}
                          </p>
                          {item.descripcion && (
                            <p className="text-xs text-base-content/50 line-clamp-2">
                              {item.descripcion}
                            </p>
                          )}
                        </div>

                        {/* Flecha */}
                        {index < documento.auditoria.length - 1 && (
                          <ChevronRight
                            className="text-base-content/30 absolute right-0 top-8 transform -translate-y-1/2"
                            size={20}
                          />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Grid de secciones */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Versiones */}
              <div className="bg-base-200 rounded-lg p-5">
                <h4 className="font-semibold text-base-content mb-4 flex items-center gap-2">
                  <FileText size={18} />
                  Versiones ({documento.versiones.length})
                </h4>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {documento.versiones.map((version) => (
                    <div
                      key={version.version_id}
                      className="bg-base-100 rounded-lg p-4 border border-base-300 hover:border-success/50 transition-colors"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-semibold text-base-content">
                              v{version.numero_version}
                            </span>
                            {version.numero_version ===
                              documento.version_actual && (
                              <span className="badge badge-success badge-sm">
                                Actual
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-base-content/60 truncate mb-1">
                            {version.archivo_nombre}
                          </p>
                          <p className="text-xs text-base-content/50">
                            {formatDate(version.fecha_subida)} •{" "}
                            {formatFileSize(version.archivo_size)}
                          </p>
                          {version.comentario && (
                            <p className="text-xs text-base-content/60 mt-2 italic">
                              "{version.comentario}"
                            </p>
                          )}
                        </div>
                        <div className="flex gap-1">
                          <button
                            onClick={() =>
                              handleDescargarArchivo(
                                version.version_id,
                                version.archivo_nombre,
                                documento.tipo_archivo,
                              )
                            }
                            className="btn btn-ghost btn-sm btn-circle"
                            title={
                              documento.tipo_archivo === "pdf"
                                ? "Ver PDF"
                                : "Descargar"
                            }
                          >
                            {documento.tipo_archivo === "pdf" ? (
                              <Eye size={16} />
                            ) : (
                              <Download size={16} />
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Revisiones */}
              <div className="bg-base-200 rounded-lg p-5">
                <h4 className="font-semibold text-base-content mb-4 flex items-center gap-2">
                  <Users size={18} />
                  Revisiones ({documento.revisiones.length})
                </h4>
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {documento.revisiones.length === 0 ? (
                    <p className="text-sm text-base-content/50 text-center py-4">
                      Aún no hay revisiones registradas
                    </p>
                  ) : (
                    documento.revisiones.map((revision) => (
                      <div
                        key={revision.revision_id}
                        className="bg-base-100 rounded-lg p-4 border border-base-300"
                      >
                        <div className="flex items-start gap-3">
                          <div
                            className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                              revision.estado === "aprobado"
                                ? "bg-green-500/20"
                                : "bg-red-500/20"
                            }`}
                          >
                            {revision.estado === "aprobado" ? (
                              <CheckCircle
                                className="text-green-600"
                                size={16}
                              />
                            ) : (
                              <XCircle className="text-red-600" size={16} />
                            )}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-2">
                                <span className="font-semibold text-sm text-base-content capitalize">
                                  {revision.estado}
                                </span>
                                <span className="text-xs text-base-content/50">
                                  • v{revision.version_revisada}
                                </span>
                              </div>
                              <span className="text-xs text-base-content/60 font-medium">
                                {(revision as any).revisor_nombre ||
                                  `Revisor ${revision.revisor_id}`}
                              </span>
                            </div>
                            <p className="text-xs text-base-content/60 mb-2">
                              {formatDate(revision.fecha_revision)}
                            </p>
                            {revision.comentarios && (
                              <p className="text-xs text-base-content/70 bg-base-200 rounded p-2">
                                {revision.comentarios}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-20">
            <XCircle className="text-error mb-4" size={48} />
            <p className="text-base-content/70">
              No se pudo cargar el documento
            </p>
          </div>
        )}
      </div>

      {/* Modales anidados */}
      {showSubirVersionModal && documento && (
        <SubirVersionModal
          isOpen={showSubirVersionModal}
          onClose={() => setShowSubirVersionModal(false)}
          documentoId={documento.documento_id}
          onSuccess={handleVersionSubida}
        />
      )}

      {showRevisarModal && documento && (
        <RevisarDocumentoModal
          isOpen={showRevisarModal}
          onClose={() => setShowRevisarModal(false)}
          documentoId={documento.documento_id}
          nombreDocumento={documento.nombre}
          onSuccess={handleRevisionRealizada}
        />
      )}
    </div>
  );

  return createPortal(modalContent, document.body);
}
