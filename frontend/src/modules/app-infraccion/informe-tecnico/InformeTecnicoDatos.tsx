import type { ReactNode } from "react";
import { CalendarDays, CheckCircle, ClipboardList, Eye, FileText, ShieldCheck, User } from "lucide-react";
import { openDocumentById } from "@shared/lib/documentViewer";
import { formatDate } from "@shared/lib/format";
import { EstadoBadge } from "@shared/ui";
import type { InformeTecnico } from "../types";

type Props = {
  titulo: string;
  informe: InformeTecnico;
  /** Nota al pie (solo en modo edición). */
  nota?: ReactNode;
  children?: ReactNode;
};

const Dato = ({ icono, label, children, destacado }: { icono: ReactNode; label: string; children: ReactNode; destacado?: boolean }) => (
  <div className="flex items-start gap-2">
    <div
      className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
        destacado ? "bg-success/10 text-success" : "bg-base-200 text-base-content/70"
      }`}
    >
      {icono}
    </div>
    <div>
      <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">{label}</p>
      <p className={`text-sm font-semibold ${destacado ? "text-success" : ""}`}>{children}</p>
    </div>
  </div>
);

const SinAsignar = () => <span className="text-base-content/60 italic">Sin asignar</span>;

/**
 * Tarjeta de datos del informe técnico en la etapa (Visita / Seguimiento).
 * Solo muestra el estado y el informe aceptado: el proceso de revisión se
 * opera desde "Mis Informes" (profesional/revisor) e "Informes Técnicos" (asignador).
 */
export default function InformeTecnicoDatos({ titulo, informe, nota, children }: Props) {
  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-success" />
            </div>
            <div>
              <h3 className="text-xl font-bold">{titulo}</h3>
              <p className="text-sm text-base-content/60">
                {informe.aceptado ? "Informe aceptado" : "Informe en proceso"}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {informe.aceptado ? (
              <EstadoBadge etiqueta="Aceptado" tono="success" size="md" icono={<CheckCircle size={14} />} />
            ) : informe.estado_proceso ? (
              <EstadoBadge etiqueta={informe.estado_proceso.etiqueta} tono={informe.estado_proceso.tono} size="md" />
            ) : (
              <EstadoBadge etiqueta="En proceso" tono="warning" size="md" />
            )}
            {informe.documento_informe_id && (
              <button
                type="button"
                onClick={() => openDocumentById(informe.documento_informe_id!)}
                className="btn btn-success btn-sm text-white gap-2"
                title="Ver informe aceptado"
              >
                <FileText size={16} />
                Ver Informe
              </button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
          <Dato icono={<User size={16} />} label="Profesional Asignado">
            {informe.profesional_nombre ?? <SinAsignar />}
          </Dato>
          <Dato icono={<Eye size={16} />} label="Revisor Asignado">
            {informe.revisor_nombre ?? <SinAsignar />}
          </Dato>
          <Dato icono={<CalendarDays size={16} />} label="Fecha Programación">
            {formatDate(informe.fecha_programacion_visita)}
          </Dato>
          <Dato icono={<ClipboardList size={16} />} label="Fecha Recibido">
            {formatDate(informe.fecha_recibido_informe)}
          </Dato>
          <Dato icono={<CheckCircle size={16} />} label="Fecha Aceptación" destacado>
            {formatDate(informe.fecha_aceptacion_informe)}
          </Dato>
        </div>

        {nota && <div className="mt-4 alert py-2 bg-base-200 border-0 text-xs text-base-content/60">{nota}</div>}

        {children}
      </div>
    </div>
  );
}
