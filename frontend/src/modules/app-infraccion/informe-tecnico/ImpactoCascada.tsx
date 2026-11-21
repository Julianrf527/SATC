import { AlertTriangle } from "lucide-react";
import { Campo } from "@shared/ui";

type Props = {
  cargando: boolean;
  error: string | null;
  etapas: { codigo: string; etiqueta: string; detalle: string }[];
};

/**
 * "También se eliminarán: …" con el detalle de cada etapa posterior que borra
 * el cambio de modo del informe (nada si no hay).
 */
export default function ImpactoCascada({ cargando, error, etapas }: Props) {
  if (cargando) {
    return (
      <p className="text-sm text-base-content/70 flex items-center gap-2" aria-live="polite">
        <span className="loading loading-spinner loading-xs" /> Revisando etapas posteriores del expediente…
      </p>
    );
  }
  if (error) {
    return (
      <p role="alert" className="text-sm text-tono-error">
        {error}. Intenta de nuevo más tarde.
      </p>
    );
  }
  if (etapas.length === 0) return null;
  return (
    <div role="alert" className="rounded-xl border border-warning/40 bg-warning/10 p-3">
      <Campo
        etiqueta={
          <span className="flex items-center gap-2 text-tono-warning">
            <AlertTriangle size={16} className="shrink-0" aria-hidden />
            También se eliminarán:
          </span>
        }
        ayuda="Incluye actos notificados y los usos de sus archivos. No se puede deshacer."
      >
        <ul className="space-y-1 text-sm text-base-content">
          {etapas.map((e) => (
            <li key={e.codigo} data-etapa={e.codigo}>
              <span className="font-semibold">{e.etiqueta}</span>
              <span className="text-base-content/70">: {e.detalle}</span>
            </li>
          ))}
        </ul>
      </Campo>
    </div>
  );
}
