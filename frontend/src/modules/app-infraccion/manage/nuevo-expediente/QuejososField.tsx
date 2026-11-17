import { Campo } from "@shared/ui/form/Campo";
import type { Quejoso } from "../../types";

type Props = {
  quejosoList: Quejoso[];
  seleccionados: number[];
  onAbrirSelector: () => void;
  disabled: boolean;
  error?: string | null;
};

/** Resumen de quejosos seleccionados + botón para abrir el selector. */
export default function QuejososField({
  quejosoList,
  seleccionados,
  onAbrirSelector,
  disabled,
  error,
}: Props) {
  return (
    <Campo etiqueta="Quejosos *" error={error}>
      <div className="bg-base-200 rounded-lg p-4 border border-base-300 space-y-3">
        <button
          type="button"
          className="btn btn-outline btn-sm"
          onClick={onAbrirSelector}
          disabled={disabled}
        >
          Seleccionar o crear quejoso
        </button>

        {seleccionados.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {quejosoList
              .filter((q) => seleccionados.includes(q.id))
              .map((q) => (
                <span
                  key={q.id}
                  className={`badge badge-outline p-3 ${q.anonimo ? "badge-warning" : "badge-success"}`}
                >
                  {q.anonimo ? "Anónimo" : q.nombre}
                </span>
              ))}
          </div>
        ) : (
          <p className="text-sm text-base-content/60">No hay quejosos seleccionados</p>
        )}
      </div>
    </Campo>
  );
}
