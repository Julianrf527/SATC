import {
  FileText,
  UserCheck,
  ExternalLink,
  CheckCircle,
  Clock,
  AlertCircle,
  Eye,
  Download,
} from "lucide-react";
import type { InformeTecnico } from "../../../../types/infraccionApp";
import { openDocumentById } from "../../../../utils/documentViewer";
import PrioridadCell from "./PrioridadCell";
import type { InformesTecnicosState } from "./useInformesTecnicos";

const formatDate = (d: string | null) => {
  if (!d) return "—";
  const [year, month, day] = d.split("T")[0].split("-");
  return `${day}/${month}/${year}`;
};

const EstadoProcesoBadge = ({ informe }: { informe: InformeTecnico }) => {
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
  if (!informe.profesional_asignado_id) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold text-error bg-error/10 px-2 py-0.5 rounded-full">
        <AlertCircle size={12} /> Sin asignar
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-semibold text-base-content/50 bg-base-200 px-2 py-0.5 rounded-full">
      <AlertCircle size={12} /> Sin proceso
    </span>
  );
};

interface Props {
  state: InformesTecnicosState;
  onGoToExpediente: (informe: InformeTecnico) => void;
  onVerProceso: (informe: InformeTecnico) => void;
  onAsignar: (informe: InformeTecnico) => void;
}

export default function InformesTable({
  state,
  onGoToExpediente,
  onVerProceso,
  onAsignar,
}: Props) {
  const {
    informes,
    loading,
    page,
    totalPages,
    handlePageChange,
    hasActiveFilters,
  } = state;

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
            <p className="text-base-content/50">
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
                        className={`badge badge-sm ${inf.tipo_informe === "VISITA" ? "badge-info" : "badge-secondary"}`}
                      >
                        {inf.tipo_informe || "—"}
                      </span>
                    </td>
                    <td className="text-xs">
                      {inf.profesional_nombre ?? (
                        <span className="text-base-content/40 italic">
                          Sin asignar
                        </span>
                      )}
                    </td>
                    <td className="text-xs">
                      {inf.revisor_nombre ?? (
                        <span className="text-base-content/40 italic">
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
                      <EstadoProcesoBadge informe={inf} />
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

                        {/* Ver proceso docs activo */}
                        {inf.proceso_activo && inf.docs_documento_id && (
                          <button
                            onClick={() => onVerProceso(inf)}
                            className="btn btn-ghost btn-xs gap-1 text-info"
                            title="Ver proceso de documentos"
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
              disabled={page <= 1 || loading}
              onClick={() => handlePageChange(page - 1)}
            >
              «
            </button>
            {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
              const p = i + 1;
              return (
                <button
                  key={p}
                  className={`btn btn-sm ${p === page ? "btn-success text-white" : "btn-ghost"}`}
                  onClick={() => handlePageChange(p)}
                  disabled={loading}
                >
                  {p}
                </button>
              );
            })}
            <button
              className="btn btn-sm btn-ghost"
              disabled={page >= totalPages || loading}
              onClick={() => handlePageChange(page + 1)}
            >
              »
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
