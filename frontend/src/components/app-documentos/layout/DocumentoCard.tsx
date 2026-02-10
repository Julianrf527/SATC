import {
  FileText,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Eye,
  Users,
  Calendar,
} from "lucide-react";

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

type Props = {
  documento: DocumentoResumen;
  onClick: () => void;
};

const formatDateShort = (dateString: string) => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("es-CO", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date);
};

const getEstadoColor = (estado: EstadoDocumento) => {
  const colors = {
    en_revision: "text-yellow-600",
    aprobado: "text-green-600",
    rechazado: "text-red-600",
    finalizado: "text-gray-600",
  };
  return colors[estado];
};

const getEstadoTexto = (estado: EstadoDocumento) => {
  const textos = {
    en_revision: "En Revisión",
    aprobado: "Aprobado",
    rechazado: "Rechazado",
    finalizado: "Finalizado",
  };
  return textos[estado];
};

const getEstadoIcon = (estado: EstadoDocumento) => {
  const icons = {
    en_revision: Clock,
    aprobado: CheckCircle,
    rechazado: XCircle,
    finalizado: AlertCircle,
  };
  return icons[estado];
};

export default function DocumentoCard({ documento, onClick }: Props) {
  const Icon = getEstadoIcon(documento.estado);

  return (
    <div
      onClick={onClick}
      className="bg-base-100 rounded-lg p-5 border border-base-300 hover:border-success/50 hover:shadow-lg transition-all cursor-pointer group"
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center group-hover:bg-success/20 transition-colors flex-shrink-0">
            <FileText className="text-success" size={20} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-base text-base-content truncate group-hover:text-success transition-colors">
              {documento.nombre}
            </h3>
            <p className="text-xs text-base-content/60">
              v{documento.version_actual}
            </p>
          </div>
        </div>
        <Eye
          size={18}
          className="text-success opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
        />
      </div>

      {/* Descripción */}
      {documento.descripcion && (
        <p className="text-sm text-base-content/70 mb-3 line-clamp-2">
          {documento.descripcion}
        </p>
      )}

      {/* Estado y métricas */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon size={16} className={getEstadoColor(documento.estado)} />
          <span
            className={`text-sm font-semibold ${getEstadoColor(
              documento.estado
            )}`}
          >
            {getEstadoTexto(documento.estado)}
          </span>
        </div>
        {documento.numero_devoluciones > 0 && (
          <span className="text-xs text-red-600 font-semibold">
            {documento.numero_devoluciones}/3 Devoluciones
          </span>
        )}
      </div>

      {/* Info adicional */}
      <div className="space-y-2 text-xs text-base-content/60">
        <div className="flex items-center gap-2">
          <Calendar size={12} />
          <span>Creado: {formatDateShort(documento.fecha_creacion)}</span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users size={12} />
            <span>{documento.total_revisores} Revisor(es)</span>
          </div>
          <span>{documento.total_revisiones} Revisión(es)</span>
        </div>
      </div>
    </div>
  );
}
