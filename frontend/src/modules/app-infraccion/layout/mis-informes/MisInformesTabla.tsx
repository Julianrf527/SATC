import { Download, ExternalLink, Eye } from "lucide-react";
import { openDocumentById } from "@shared/lib/documentViewer";
import { formatDate } from "@shared/lib/format";
import type { MiInforme } from "../../types";
import EstadoInformeBadge from "../../informe-tecnico/EstadoInformeBadge";
import MatrizCell from "./MatrizCell";

type Props = {
  informes: MiInforme[];
  onExpediente: (informe: MiInforme) => void;
  onProceso: (informe: MiInforme) => void;
  /** Precarga el proceso al pasar el mouse (abre sin spinner). */
  onPrecargarProceso?: (informe: MiInforme) => void;
  onMatriz: (informe: MiInforme) => void;
};

export default function MisInformesTabla({ informes, onExpediente, onProceso, onPrecargarProceso, onMatriz }: Props) {
  return (
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
            <th className="text-xs text-center border-l border-base-300">Informe</th>
            <th className="text-xs text-center border-l border-base-300">Matriz</th>
          </tr>
        </thead>
        <tbody>
          {informes.map((inf) => (
            <tr key={inf.id} className={`border-b border-base-200 ${inf.requiere_mi_accion ? "bg-info/5" : ""}`}>
              <td className="font-mono text-xs font-semibold">
                <button type="button" onClick={() => onExpediente(inf)} className="btn btn-ghost btn-xs gap-1 text-primary">
                  {inf.expediente_radicado ?? `#${inf.expediente_id}`}
                  <ExternalLink size={10} />
                </button>
              </td>
              <td>
                <span className={`badge badge-sm text-white ${inf.tipo_informe === "VISITA" ? "badge-info" : "badge-secondary"}`}>
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
                <EstadoInformeBadge informe={inf} />
              </td>
              <td className="text-center border-l border-base-200">
                <div className="flex items-center justify-center gap-1">
                  {inf.aceptado && inf.documento_informe_id && (
                    <button
                      type="button"
                      onClick={() => openDocumentById(inf.documento_informe_id!)}
                      className="btn btn-ghost btn-xs gap-1 text-success"
                      title="Ver documento aceptado"
                    >
                      <Download size={13} />
                      Ver doc
                    </button>
                  )}
                  {inf.proceso_id !== null && (
                    <button
                      type="button"
                      onClick={() => onProceso(inf)}
                      onMouseEnter={() => onPrecargarProceso?.(inf)}
                      onFocus={() => onPrecargarProceso?.(inf)}
                      className={`btn btn-xs gap-1 ${inf.requiere_mi_accion ? "btn-info text-white" : "btn-ghost text-info"}`}
                    >
                      <Eye size={13} />
                      Proceso
                    </button>
                  )}
                  {!inf.documento_informe_id && inf.proceso_id === null && (
                    <span className="text-xs text-base-content/60">—</span>
                  )}
                </div>
              </td>
              <td className="text-center border-l border-base-200">
                <MatrizCell informe={inf} onOpen={() => onMatriz(inf)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
