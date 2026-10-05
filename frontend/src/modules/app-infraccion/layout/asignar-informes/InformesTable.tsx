import { Download, ExternalLink, Eye, FileText, UserCheck } from "lucide-react";
import { openDocumentById } from "@shared/lib/documentViewer";
import { formatDate } from "@shared/lib/format";
import type { InformeTecnico } from "../../types";
import EstadoInformeBadge from "../../informe-tecnico/EstadoInformeBadge";
import PrioridadCell from "./PrioridadCell";
import type { InformesTecnicosState } from "./useInformesTecnicos";

interface Props {
  state: InformesTecnicosState;
  onGoToExpediente: (informe: InformeTecnico) => void;
  onVerProceso: (informe: InformeTecnico) => void;
  /** Precarga el proceso al pasar el mouse (abre sin spinner). */
  onPrecargarProceso?: (informe: InformeTecnico) => void;
  onAsignar: (informe: InformeTecnico) => void;
}

export default function InformesTable({
  state,
  onGoToExpediente,
  onVerProceso,
  onPrecargarProceso,
  onAsignar,
}: Props) {
  const { informes, loading, fetching, page, totalPages, setPage, hasActiveFilters } = state;

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-0">
        {loading ? (
          <div className="flex justify-center items-center py-16">
            <span className="loading loading-spinner loading-lg text-success" />
          </div>
        ) : informes.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <FileText className="w-12 h-12 text-base-content/20 mb-3" />
            <p className="text-base-content/60">
              {hasActiveFilters
                ? "Sin resultados con los filtros aplicados"
                : "No hay informes técnicos registrados"}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="table table-sm w-full">
              <thead className="bg-base-200">
                <tr>
                  <th className="text-xs">Expediente</th>
                  <th className="text-xs">Tipo</th>
                  <th className="text-xs">Profesional</th>
                  <th className="text-xs">Revisor</th>
                  <th className="text-xs">Fecha Programación</th>
                  <th className="text-xs">Fecha Recibido</th>
                  <th className="text-xs">Fecha Aceptación</th>
                  <th className="text-xs">Estado</th>
                  <th className="text-xs">Prioridad</th>
                  <th className="text-xs text-center">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {informes.map((inf) => (
                  <tr
                    key={inf.id}
                    className="hover:bg-base-50 border-b border-base-200"
                  >
                    <td className="font-mono text-xs font-semibold">
                      <button
                        onClick={() => onGoToExpediente(inf)}
                        className="btn btn-ghost btn-xs gap-1 text-primary"
                        title="Ver expediente"
                      >
                        {inf.expediente_radicado ?? `#${inf.expediente_id}`}
                        <ExternalLink size={10} />
                      </button>
                    </td>
                    <td>
                      <span
                        className={`badge badge-sm text-white ${inf.tipo_informe === "VISITA" ? "badge-info" : "badge-secondary"}`}
                      >
                        {inf.tipo_informe || "—"}
                      </span>
                    </td>
                    <td className="text-xs">
                      {inf.profesional_nombre ?? (
                        <span className="text-base-content/60 italic">
                          Sin asignar
                        </span>
                      )}
                    </td>
                    <td className="text-xs">
                      {inf.revisor_nombre ?? (
                        <span className="text-base-content/60 italic">
                          Sin asignar
                        </span>
                      )}
                    </td>
                    <td className="text-xs">
                      {formatDate(inf.fecha_programacion_visita)}
                    </td>
                    <td className="text-xs">
                      {formatDate(inf.fecha_recibido_informe)}
                    </td>
                    <td className="text-xs">
                      {formatDate(inf.fecha_aceptacion_informe)}
                    </td>
                    <td>
                      <EstadoInformeBadge informe={inf} />
                    </td>
                    {/* Prioridad */}
                    <td>
                      <PrioridadCell informe={inf} />
                    </td>
                    <td>
                      <div className="flex items-center justify-center gap-1">
                        {/* Ver documento aceptado */}
                        {inf.aceptado && inf.documento_informe_id && (
                          <button
                            onClick={() =>
                              openDocumentById(inf.documento_informe_id!)
                            }
                            className="btn btn-ghost btn-xs gap-1 text-success"
                            title="Ver documento aceptado"
                          >
                            <Download size={13} />
                            Ver doc
                          </button>
                        )}

                        {/* Proceso de revisión (vigente o último) */}
                        {inf.proceso_id !== null && (
                          <button
                            onClick={() => onVerProceso(inf)}
                            onMouseEnter={() => onPrecargarProceso?.(inf)}
                            onFocus={() => onPrecargarProceso?.(inf)}
                            className="btn btn-ghost btn-xs gap-1 text-tono-info"
                            title="Ver proceso de revisión"
                          >
                            <Eye size={13} />
                            Proceso
                          </button>
                        )}

                        {/* Asignar / Reasignar */}
                        {!inf.aceptado && (
                          <button
                            onClick={() => onAsignar(inf)}
                            className="btn btn-ghost btn-xs gap-1 text-success"
                            title={
                              inf.profesional_asignado_id
                                ? "Reasignar profesional"
                                : "Asignar profesional"
                            }
                          >
                            <UserCheck size={13} />
                            {inf.profesional_asignado_id
                              ? "Reasignar"
                              : "Asignar"}
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

        {/* Paginación */}
        {totalPages > 1 && (
          <div className="flex justify-center items-center gap-2 p-4 border-t border-base-200">
            <button
              className="btn btn-sm btn-ghost"
              disabled={page <= 1 || fetching}
              onClick={() => setPage(page - 1)}
            >
              «
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              const p = i + 1;
              return (
                <button
                  key={p}
                  className={`btn btn-sm ${p === page ? "btn-success text-white" : "btn-ghost"}`}
                  onClick={() => setPage(p)}
                  disabled={fetching}
                >
                  {p}
                </button>
              );
            })}
            <button
              className="btn btn-sm btn-ghost"
              disabled={page >= totalPages || fetching}
              onClick={() => setPage(page + 1)}
            >
              »
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
