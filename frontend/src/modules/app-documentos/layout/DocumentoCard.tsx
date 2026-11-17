import { Calendar, Eye, FileText, Users } from "lucide-react";
import { EstadoBadge } from "@shared/ui";
import { formatDate } from "@shared/lib/format";
import type { DocumentoResumen } from "../types";

type Props = {
  documento: DocumentoResumen;
  onClick: () => void;
  /** Precarga el detalle al pasar el mouse (abre sin spinner). */
  onPrecargar?: () => void;
};

export default function DocumentoCard({ documento, onClick, onPrecargar }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      onMouseEnter={onPrecargar}
      onFocus={onPrecargar}
      className="w-full text-left bg-base-100 rounded-lg p-5 border border-base-300 hover:border-success/50 hover:shadow-lg transition-all cursor-pointer group"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center group-hover:bg-success/20 transition-colors shrink-0">
            <FileText className="text-success" size={20} />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-base text-base-content truncate group-hover:text-success transition-colors">
              {documento.nombre}
            </h3>
            <p className="text-xs text-base-content/60">v{documento.version_actual ?? 0}</p>
          </div>
        </div>
        <Eye size={18} className="text-success opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
      </div>

      {documento.descripcion && (
        <p className="text-sm text-base-content/70 mb-3 line-clamp-2">{documento.descripcion}</p>
      )}

      <div className="flex items-center justify-between mb-3">
        <EstadoBadge etiqueta={documento.estado.etiqueta} tono={documento.estado.tono} />
        {documento.numero_devoluciones > 0 && (
          <span className="text-xs text-error font-semibold">
            {documento.numero_devoluciones} devolución(es)
          </span>
        )}
      </div>

      <div className="space-y-2 text-xs text-base-content/60">
        <div className="flex items-center gap-2">
          <Calendar size={12} />
          <span>Creado: {formatDate(documento.fecha_creacion)}</span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users size={12} />
            <span>{documento.total_revisores} Revisor(es)</span>
          </div>
          <span>{documento.total_revisiones} Revisión(es)</span>
        </div>
      </div>
    </button>
  );
}
