import type { ReactNode } from "react";
import { ChevronRight } from "lucide-react";

export type CampoTarjeta = {
  etiqueta: string;
  valor: ReactNode;
  icono: ReactNode;
};

type Props = {
  titulo: string;
  campos: CampoTarjeta[];
  onClick: () => void;
};

/** Tarjeta clicable de un expediente en la lista lateral. */
export default function ExpedienteCard({ titulo, campos, onClick }: Props) {
  return (
    <div
      className="card bg-base-100 border border-base-300 cursor-pointer
                 hover:border-success hover:shadow-lg transition-all duration-200
                 hover:-translate-y-0.5 active:translate-y-0"
      onClick={onClick}
    >
      <div className="card-body p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="card-title text-base font-bold truncate">{titulo}</h3>
        </div>

        <div className="space-y-2">
          {campos.map((c) => (
            <div key={c.etiqueta} className="flex items-start gap-2">
              <span className="w-4 h-4 text-base-content/40 mt-0.5 flex-shrink-0 [&>svg]:w-4 [&>svg]:h-4">
                {c.icono}
              </span>
              <div>
                <p className="text-xs text-base-content/60 uppercase tracking-wide font-medium">
                  {c.etiqueta}
                </p>
                <p className="text-sm text-base-content leading-tight">{c.valor}</p>
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
