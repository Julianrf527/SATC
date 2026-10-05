import { Check } from "lucide-react";
import type { RevisorDisponible } from "../types";

type Props = {
  revisores: RevisorDisponible[];
  seleccionados: number[];
  onChange: (ids: number[]) => void;
  disabled?: boolean;
};

/** Chips seleccionables de revisores (selección múltiple). */
export default function RevisoresSelector({ revisores, seleccionados, onChange, disabled }: Props) {
  const alternar = (id: number) =>
    onChange(seleccionados.includes(id) ? seleccionados.filter((x) => x !== id) : [...seleccionados, id]);

  return (
    <div>
      <div className="border border-base-300 rounded-lg p-3 bg-base-100 max-h-48 overflow-y-auto space-y-2">
        {revisores.length === 0 ? (
          <p className="text-sm text-base-content/60 text-center py-2">No hay revisores disponibles</p>
        ) : (
          revisores.map((revisor) => {
            const activo = seleccionados.includes(revisor.id);
            return (
              <button
                key={revisor.id}
                type="button"
                role="checkbox"
                aria-checked={activo}
                onClick={() => alternar(revisor.id)}
                disabled={disabled}
                className={`w-full text-left px-4 py-3 rounded-lg border-2 transition-all ${
                  activo ? "border-success bg-success/10 shadow-sm" : "border-base-300 hover:border-base-content/30"
                }`}
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
                      activo ? "border-success bg-success text-white" : "border-base-300"
                    }`}
                  >
                    {activo && <Check size={12} strokeWidth={3} />}
                  </span>
                  <span className="flex-1 min-w-0">
                    <span className={`block text-sm font-medium truncate ${activo ? "text-success" : "text-base-content"}`}>
                      {revisor.nombre_completo}
                    </span>
                    <span className="block text-xs text-base-content/60 truncate">{revisor.email}</span>
                  </span>
                </div>
              </button>
            );
          })
        )}
      </div>
      {seleccionados.length > 0 && (
        <p className="mt-2 badge badge-success gap-1">
          <Check size={12} /> {seleccionados.length} seleccionado{seleccionados.length > 1 ? "s" : ""}
        </p>
      )}
    </div>
  );
}
