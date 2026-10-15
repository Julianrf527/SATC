import { useState, type ComponentProps } from "react";
import { DatabaseZap, FileSignature } from "lucide-react";
import SuperCargueModal from "./SuperCargueModal";

type SuperProps = Omit<ComponentProps<typeof SuperCargueModal>, "onClose">;

/** "Cargue directo" de super gestión (solo si el nodo trae `super_cargar`). */
export function BotonSuperCargue(props: SuperProps) {
  const [abierto, setAbierto] = useState(false);
  return (
    <>
      <button
        type="button"
        className="btn btn-outline btn-warning btn-sm gap-1.5"
        onClick={() => setAbierto(true)}
        title="Cargue directo sin revisión (super gestión)"
      >
        <DatabaseZap size={14} />
        Cargue directo
      </button>
      {abierto && <SuperCargueModal {...props} onClose={() => setAbierto(false)} />}
    </>
  );
}

/** Botón "Cargar versión final" (documento aprobado para firma). */
export function BotonVersionFinal({ onClick }: { onClick: () => void }) {
  return (
    <button type="button" className="btn btn-success btn-sm text-white gap-1.5" onClick={onClick}>
      <FileSignature size={14} />
      Cargar versión final
    </button>
  );
}
