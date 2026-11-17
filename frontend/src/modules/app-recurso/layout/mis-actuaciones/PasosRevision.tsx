import { CheckCircle2, Circle, Clock } from "lucide-react";
import type { PasoRevision } from "../../types";

/**
 * Cadena de revisión del documento (B.1 `pasos`): en cada paso revisan
 * todos los permisos, en cualquier orden. Solo pinta lo que manda el backend.
 */
export default function PasosRevision({ pasos }: { pasos: PasoRevision[] }) {
  if (pasos.length === 0) return null;
  return (
    <div className="border border-base-300 rounded-lg p-3">
      <p className="text-xs font-semibold text-base-content/60 uppercase tracking-wider mb-2">Cadena de revisión</p>
      <ol className="flex flex-col md:flex-row gap-3">
        {pasos.map((paso) => (
          <li
            key={paso.numero}
            className={`flex-1 rounded-lg border p-2 ${
              paso.estado === "actual"
                ? "border-info bg-info/5"
                : paso.estado === "completado"
                  ? "border-success/40 bg-success/5"
                  : "border-base-300"
            }`}
          >
            <p className="text-xs font-semibold mb-1">
              Paso {paso.numero}
              {paso.estado === "actual" && <span className="badge badge-info badge-xs text-white ml-2">actual</span>}
            </p>
            <ul className="space-y-1">
              {paso.permisos.map((p) => (
                <li key={p.permiso} className="flex items-start gap-1.5 text-xs">
                  {p.revisado ? (
                    <CheckCircle2 size={13} className="text-success mt-0.5 flex-shrink-0" />
                  ) : paso.estado === "actual" ? (
                    <Clock size={13} className="text-info mt-0.5 flex-shrink-0" />
                  ) : (
                    <Circle size={13} className="text-base-content/40 mt-0.5 flex-shrink-0" />
                  )}
                  <span>
                    <span className="font-medium">{p.etiqueta}</span>
                    {p.revisado && p.revisor_nombre && <span className="text-base-content/60"> · {p.revisor_nombre}</span>}
                  </span>
                </li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </div>
  );
}
