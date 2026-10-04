import { Leaf } from "lucide-react";
import type { FilaRecursoAfectado, RecursoMatriz } from "../../../types/infraccionApp";

const RECURSO_LABELS: Record<RecursoMatriz, string> = {
  AIRE: "Aire",
  SUELO: "Suelo",
  AGUA: "Agua",
  PAISAJE: "Paisaje",
  FLORA: "Flora",
  FAUNA: "Fauna",
  RUIDO: "Ruido",
  SOCIAL: "Social",
  OTRO: "Otro",
};

const Marca = ({ activo }: { activo: boolean }) =>
  activo ? <span className="font-bold text-success">X</span> : null;

type Props = {
  filas: FilaRecursoAfectado[];
  action?: React.ReactNode;
};

export default function MatrizRecursosAfectadosView({ filas, action }: Props) {
  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body gap-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-success/10 rounded-lg flex items-center justify-center">
              <Leaf className="text-success" size={18} />
            </div>
            <div>
              <h4 className="font-bold">Recursos Afectados</h4>
              <p className="text-xs text-base-content/60">Matriz de magnitud y reversibilidad</p>
            </div>
          </div>
          {action}
        </div>

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
                const noExiste = f.no_existe || !f.magnitud;
                return (
                  <tr key={f.recurso}>
                    <td className="font-medium">{RECURSO_LABELS[f.recurso]}</td>
                    <td className="text-center border-l border-base-300"><Marca activo={f.magnitud === "LEVE"} /></td>
                    <td className="text-center"><Marca activo={f.magnitud === "MODERADO"} /></td>
                    <td className="text-center"><Marca activo={f.magnitud === "GRAVE"} /></td>
                    <td className="text-center border-l border-base-300"><Marca activo={f.reversibilidad === "REVERSIBLE"} /></td>
                    <td className="text-center"><Marca activo={f.reversibilidad === "IRREVERSIBLE"} /></td>
                    <td className="text-center border-l border-base-300"><Marca activo={noExiste} /></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
