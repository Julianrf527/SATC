import type { ReactNode } from "react";
import Icono from "./Icono";

type Props = {
  icono: string;
  etiqueta: string;
  children: ReactNode;
  /** Clases del contenedor del valor (p. ej. "flex-1"). */
  className?: string;
};

/** Dato de solo lectura: icono cuadrado + etiqueta en mayúsculas + valor. */
export default function InfoItem({ icono, etiqueta, children, className }: Props) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
        <Icono d={icono} className="w-4 h-4 text-base-content/70" />
      </div>
      <div className={className}>
        <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
          {etiqueta}
        </p>
        {children}
      </div>
    </div>
  );
}
