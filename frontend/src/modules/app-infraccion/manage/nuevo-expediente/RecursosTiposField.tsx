import { ChevronDown } from "lucide-react";
import { Campo } from "@shared/ui/form/Campo";
import type { ModeloGenerico } from "@shared/types/common";
import type { TipoAfectacion } from "../../types";

type Props = {
  recursoAfectadoList: ModeloGenerico[];
  tipoAfectacionList: TipoAfectacion[];
  recursosSeleccionados: number[];
  tiposSeleccionados: number[];
  expandidos: number[];
  onToggleRecurso: (id: number) => void;
  onToggleTipo: (id: number) => void;
  onToggleExpandir: (id: number) => void;
  disabled: boolean;
  /** Error a mostrar bajo la lista (ya filtrado por el padre). */
  error?: string | null;
};

/** Recursos afectados con sus tipos de afectación anidados (acordeón). */
export default function RecursosTiposField({
  recursoAfectadoList,
  tipoAfectacionList,
  recursosSeleccionados,
  tiposSeleccionados,
  expandidos,
  onToggleRecurso,
  onToggleTipo,
  onToggleExpandir,
  disabled,
  error,
}: Props) {
  return (
    <Campo etiqueta="Recursos Afectados *" error={error}>
      <div className="border border-base-300 rounded-lg overflow-hidden divide-y divide-base-300">
        {recursoAfectadoList.map((r) => {
          const isSelected = recursosSeleccionados.includes(r.id);
          const isExpanded = expandidos.includes(r.id);
          const tipos = tipoAfectacionList.filter((t) => t.recurso_id === r.id);
          return (
            <div key={r.id}>
              <div
                className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                  isSelected ? "bg-success/5" : "bg-base-100 hover:bg-base-200"
                }`}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => onToggleRecurso(r.id)}
                  className="checkbox checkbox-success checkbox-sm flex-shrink-0"
                  disabled={disabled}
                />
                <span
                  className="flex-1 text-sm font-semibold text-base-content cursor-pointer select-none"
                  onClick={() => onToggleRecurso(r.id)}
                >
                  {r.nombre}
                </span>
                {tipos.length > 0 && (
                  <button
                    type="button"
                    onClick={() => onToggleExpandir(r.id)}
                    className="btn btn-ghost btn-xs btn-circle"
                    disabled={disabled}
                  >
                    <ChevronDown
                      className={`w-4 h-4 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                    />
                  </button>
                )}
              </div>
              {isExpanded && tipos.length > 0 && (
                <div className="bg-base-200/50 border-t border-base-300 px-4 py-2 space-y-0.5">
                  {tipos.map((tipo) => (
                    <label
                      key={tipo.id}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                        isSelected ? "hover:bg-base-200" : "opacity-40 cursor-not-allowed"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={tiposSeleccionados.includes(tipo.id)}
                        onChange={() => onToggleTipo(tipo.id)}
                        className="checkbox checkbox-success checkbox-xs flex-shrink-0"
                        disabled={disabled || !isSelected}
                      />
                      <span className="text-sm text-base-content">{tipo.nombre}</span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </Campo>
  );
}
