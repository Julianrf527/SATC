import { ExternalLink, Eye } from "lucide-react";
import { EstadoBadge } from "@shared/ui";
import { formatDate } from "@shared/lib/format";
import { etiquetaRol } from "../../api/misDocumentosParams";
import type { MiDocumento } from "../../types";

type Props = {
  documentos: MiDocumento[];
  onProceso: (doc: MiDocumento) => void;
  onPrecargarProceso?: (doc: MiDocumento) => void;
  /** `undefined` si el usuario no puede abrir el expediente (sin Gestionar ni Consulta). */
  onExpediente?: (doc: MiDocumento) => void;
};

/** Tabla de Mis informes: todos mis documentos; resalta los que requieren mi acción. Todo viene del backend. */
export default function MisDocumentosTabla({ documentos, onProceso, onPrecargarProceso, onExpediente }: Props) {
  return (
    <div className="overflow-x-auto">
      <table className="table table-sm w-full">
        <thead className="bg-base-200">
          <tr>
            <th className="text-xs">Expediente</th>
            <th className="text-xs">Documento</th>
            <th className="text-xs">Rol</th>
            <th className="text-xs">Etapa</th>
            <th className="text-xs">Estado</th>
            <th className="text-xs">Paso</th>
            <th className="text-xs">Pendiente</th>
            <th className="text-xs">Actualizado</th>
            <th className="text-xs text-center border-l border-base-300">Proceso</th>
          </tr>
        </thead>
        <tbody>
          {documentos.map((doc) => {
            const codigo = doc.expediente_codigo ?? doc.expediente_radicado ?? `#${doc.expediente_id}`;
            return (
              <tr key={doc.proceso_id} className={`border-b border-base-200 ${doc.requiere_mi_accion ? "bg-info/5" : ""}`}>
                <td className="font-mono text-xs font-semibold">
                  {onExpediente ? (
                    <button type="button" onClick={() => onExpediente(doc)} className="btn btn-ghost btn-xs gap-1 text-primary">
                      {codigo}
                      <ExternalLink size={10} />
                    </button>
                  ) : (
                    codigo
                  )}
                  {doc.expediente_radicado && doc.expediente_codigo && (
                    <p className="text-[10px] font-normal text-base-content/60 px-2">{doc.expediente_radicado}</p>
                  )}
                </td>
                <td className="text-xs">{doc.tipo_documento_etiqueta}</td>
                <td className="text-xs">
                  <div className="flex gap-1">
                    {doc.roles.map((r) => (
                      <span key={r} className="badge badge-ghost badge-xs">
                        {etiquetaRol(r)}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="text-xs">{doc.etapa_padre_etiqueta ?? doc.etapa_etiqueta}</td>
                <td>
                  <EstadoBadge etiqueta={doc.estado_proceso.etiqueta} tono={doc.estado_proceso.tono} />
                  {!doc.proceso_activo && doc.estado_proceso.codigo !== "aprobado" && doc.estado_proceso.codigo !== "finalizado" && (
                    <p className="text-[10px] text-base-content/60 mt-0.5">No vigente</p>
                  )}
                </td>
                <td className="text-xs">
                  {doc.paso_actual}/{doc.total_pasos}
                  {doc.permisos_pendientes.length > 0 && (
                    <p className="text-[10px] text-base-content/60">{doc.permisos_pendientes.map((p) => p.etiqueta).join(", ")}</p>
                  )}
                </td>
                <td className="text-xs">
                  {doc.accion_pendiente ?? <span className="text-base-content/60">—</span>}
                  {doc.numero_devoluciones > 0 && (
                    <span className="badge badge-warning badge-xs ml-1" title="Devoluciones">
                      {doc.numero_devoluciones}
                    </span>
                  )}
                </td>
                <td className="text-xs">{formatDate(doc.fecha_ultima_actualizacion ?? doc.fecha_creacion)}</td>
                <td className="text-center border-l border-base-200">
                  <button
                    type="button"
                    onClick={() => onProceso(doc)}
                    onMouseEnter={() => onPrecargarProceso?.(doc)}
                    onFocus={() => onPrecargarProceso?.(doc)}
                    className={`btn btn-xs gap-1 ${doc.requiere_mi_accion ? "btn-info text-white" : "btn-ghost text-info"}`}
                  >
                    <Eye size={13} />
                    Proceso
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
