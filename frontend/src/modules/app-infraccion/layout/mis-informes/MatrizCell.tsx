import type { ReactNode } from "react";
import { CheckCircle, Clock, Leaf, Lock, Minus } from "lucide-react";
import type { MiInforme } from "../../types";

const Aviso = ({ icono, label, title }: { icono: ReactNode; label: string; title?: string }) => (
  <span className="inline-flex items-center gap-1 text-xs text-base-content/60" title={title}>
    {icono} {label}
  </span>
);

/** Columna "Matriz" de Mis Informes (solo informes de VISITA aceptados). */
export default function MatrizCell({ informe, onOpen }: { informe: MiInforme; onOpen: () => void }) {
  if (informe.tipo_informe !== "VISITA") {
    return <Aviso icono={<Minus size={12} />} label="No aplica" title="La matriz solo aplica a informes de visita" />;
  }
  if (!informe.aceptado) {
    return <Aviso icono={<Lock size={12} />} label="Bloqueada" title="Disponible cuando el informe sea aceptado" />;
  }
  if (informe.puede_diligenciar_matriz) {
    return (
      <button type="button" onClick={onOpen} className="btn btn-ghost btn-xs gap-1 text-success">
        <Leaf size={13} />
        {informe.tiene_matriz ? "Editar matriz" : "Diligenciar"}
      </button>
    );
  }
  return informe.tiene_matriz ? (
    <span className="inline-flex items-center gap-1 text-xs text-success">
      <CheckCircle size={12} /> Diligenciada
    </span>
  ) : (
    <Aviso icono={<Clock size={12} />} label="Pendiente" title="La diligencia el profesional asignado" />
  );
}
