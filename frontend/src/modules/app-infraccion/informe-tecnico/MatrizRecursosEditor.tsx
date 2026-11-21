import type { FilaRecursoAfectado, RecursoMatriz } from "../types";
import { MAGNITUDES, RECURSO_LABELS, REVERSIBILIDADES, type Magnitud, type Reversibilidad } from "./recursos";

/**
 * Matriz de recursos afectados (informes de VISITA), controlada. La usan:
 * editar matriz (modal), "Cargar versión final" y el cargue manual. El
 * backend exige la matriz completa: una fila por recurso, con magnitud y
 * reversibilidad o "no existe" (aquí: sin magnitud = no existe). Helpers
 * (matrizInicial, errorMatriz, normalizarMatriz) en ./recursos.
 */

type Props = {
  filas: FilaRecursoAfectado[];
  onChange: (filas: FilaRecursoAfectado[]) => void;
  disabled?: boolean;
};

export default function MatrizRecursosEditor({ filas, onChange, disabled }: Props) {
  const actualizar = (recurso: RecursoMatriz, cambio: (f: FilaRecursoAfectado) => FilaRecursoAfectado) =>
    onChange(filas.map((f) => (f.recurso === recurso ? cambio(f) : f)));

  const toggleMagnitud = (recurso: RecursoMatriz, m: Magnitud) =>
    actualizar(recurso, (f) => (f.magnitud === m ? { ...f, magnitud: null, reversibilidad: null } : { ...f, magnitud: m }));

  const toggleReversibilidad = (recurso: RecursoMatriz, r: Reversibilidad) =>
    actualizar(recurso, (f) => ({ ...f, reversibilidad: f.reversibilidad === r ? null : r }));

  return (
    <div className="overflow-x-auto">
      <table className="table table-sm w-full">
        <thead>
          <tr>
            <th rowSpan={2} className="align-bottom">Recurso Afectado</th>
            <th colSpan={3} className="text-center border-l border-base-300">Magnitud</th>
            <th colSpan={2} className="text-center border-l border-base-300">Reversibilidad</th>
            <th rowSpan={2} className="text-center align-bottom border-l border-base-300">No existe</th>
          </tr>
          <tr>
            <th className="text-center border-l border-base-300">Leve</th>
            <th className="text-center">Moderado</th>
            <th className="text-center">Grave</th>
            <th className="text-center border-l border-base-300">Reversible</th>
            <th className="text-center">Irreversible</th>
          </tr>
        </thead>
        <tbody>
          {filas.map((f) => {
            const noExiste = !f.magnitud;
            const nombre = RECURSO_LABELS[f.recurso];
            return (
              <tr key={f.recurso}>
                <td className="font-medium">{nombre}</td>
                {MAGNITUDES.map((m, i) => (
                  <td key={m} className={`text-center ${i === 0 ? "border-l border-base-300" : ""}`}>
                    <input
                      type="radio"
                      aria-label={`${nombre}: ${m.toLowerCase()}`}
                      className="radio radio-success radio-sm"
                      checked={f.magnitud === m}
                      disabled={disabled}
                      onChange={() => {}}
                      onClick={() => toggleMagnitud(f.recurso, m)}
                    />
                  </td>
                ))}
                {REVERSIBILIDADES.map((r, i) => (
                  <td key={r} className={`text-center ${i === 0 ? "border-l border-base-300" : ""}`}>
                    <input
                      type="radio"
                      aria-label={`${nombre}: ${r.toLowerCase()}`}
                      className="radio radio-success radio-sm"
                      checked={f.reversibilidad === r}
                      disabled={disabled || noExiste}
                      onChange={() => {}}
                      onClick={() => toggleReversibilidad(f.recurso, r)}
                    />
                  </td>
                ))}
                <td className="text-center border-l border-base-300">
                  <input
                    type="checkbox"
                    aria-label={`${nombre}: no existe`}
                    className="checkbox checkbox-sm"
                    checked={noExiste}
                    disabled
                    readOnly
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
