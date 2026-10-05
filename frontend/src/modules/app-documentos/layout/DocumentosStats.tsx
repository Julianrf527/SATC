import type { ReactNode } from "react";
import { Eye, Upload } from "lucide-react";
import type { EstadisticasDocumentos } from "../types";

type Fila = { label: string; valor: number; className?: string };

function Tarjeta({ icono, titulo, filas }: { icono: ReactNode; titulo: string; filas: Fila[] }) {
  return (
    <div className="bg-base-100 rounded-lg p-4 shadow-lg border border-base-300">
      <div className="flex items-center gap-2 mb-4">
        {icono}
        <h3 className="text-sm font-semibold text-base-content">{titulo}</h3>
      </div>
      <dl className="space-y-3">
        {filas.map((f) => (
          <div key={f.label} className="flex items-center justify-between">
            <dt className="text-xs text-base-content/70">{f.label}</dt>
            <dd className={`text-lg font-bold ${f.className ?? "text-base-content"}`}>{f.valor}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

/** Panel lateral de estadísticas (solo las secciones que el usuario tiene). */
export default function DocumentosStats({ stats }: { stats: EstadisticasDocumentos }) {
  return (
    <div className="space-y-4 sticky top-24">
      {stats.revisor && (
        <Tarjeta
          titulo="Revisiones"
          icono={
            <div className="w-8 h-8 bg-info/10 rounded-lg flex items-center justify-center">
              <Eye className="text-tono-info" size={16} />
            </div>
          }
          filas={[
            { label: "Asignados", valor: stats.revisor.total_asignados },
            { label: "Pendientes", valor: stats.revisor.pendientes, className: "text-tono-warning" },
            { label: "Aprobados", valor: stats.revisor.aprobados, className: "text-success" },
            { label: "Devueltos", valor: stats.revisor.devueltos, className: "text-error" },
          ]}
        />
      )}
      {stats.creador && (
        <Tarjeta
          titulo="Mis Documentos"
          icono={
            <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
              <Upload className="text-primary" size={16} />
            </div>
          }
          filas={[
            { label: "Total Creados", valor: stats.creador.total_creados },
            { label: "En Revisión", valor: stats.creador.en_revision, className: "text-tono-warning" },
            { label: "Aprobados", valor: stats.creador.aprobados, className: "text-success" },
            { label: "Devueltos", valor: stats.creador.rechazados, className: "text-error" },
          ]}
        />
      )}
    </div>
  );
}
