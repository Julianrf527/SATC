import { CalendarPlus, ChevronRight, FileText, MapPin } from "lucide-react";
import { formatDate } from "@shared/lib/format";
import type { ExpedienteResumen } from "../../types";

type Props = {
  expediente: ExpedienteResumen;
  seleccionado: boolean;
  onClick: () => void;
};

/**
 * Tarjeta de la lista lateral. Réplica visual de la tarjeta de
 * `@features/expedientes` (no se exporta desde su index), con los datos
 * propios de una concesión: número de expediente, radicado, municipio y fecha.
 */
export default function ExpedienteCard({ expediente: e, seleccionado, onClick }: Props) {
  const campos = [
    { etiqueta: "Radicado", valor: e.radicado, icono: <FileText /> },
    { etiqueta: "Municipio", valor: e.municipio?.nombre || "Desconocido", icono: <MapPin /> },
    { etiqueta: "Fecha de Creación", valor: formatDate(e.fecha_creacion), icono: <CalendarPlus /> },
  ];

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onClick}
      onKeyDown={(ev) => {
        if (ev.key === "Enter" || ev.key === " ") {
          ev.preventDefault();
          onClick();
        }
      }}
      className={`card bg-base-100 border cursor-pointer hover:border-success hover:shadow-lg transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 ${
        seleccionado ? "border-success shadow-md" : "border-base-300"
      }`}
    >
      <div className="card-body p-4">
        <div className="mb-3">
          <h3 className="card-title text-base font-bold truncate">{e.expediente}</h3>
        </div>

        <div className="space-y-2">
          {campos.map((c) => (
            <div key={c.etiqueta} className="flex items-start gap-2">
              <span className="w-4 h-4 text-base-content/40 mt-0.5 flex-shrink-0 [&>svg]:w-4 [&>svg]:h-4">{c.icono}</span>
              <div className="min-w-0">
                <p className="text-xs text-base-content/60 uppercase tracking-wide font-medium">{c.etiqueta}</p>
                <p className="text-sm text-base-content leading-tight truncate">{c.valor}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-3 pt-3 border-t border-base-300">
          <div className="flex items-center justify-between">
            <span className="text-xs text-base-content/60">Click para ver detalles</span>
            <ChevronRight className="w-4 h-4 text-base-content/40" />
          </div>
        </div>
      </div>
    </div>
  );
}
