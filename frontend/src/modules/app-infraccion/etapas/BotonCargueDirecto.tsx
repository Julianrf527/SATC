import { DatabaseZap } from "lucide-react";

/**
 * "Cargue directo" de super gestión (réplica de `BotonSuperCargue` de
 * recurso): misma estética en la cabecera de cada etapa / acto. Quien lo
 * pinta decide si el usuario puede (permiso + `isEditable`).
 */
export default function BotonCargueDirecto({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      className="btn btn-outline btn-warning btn-sm gap-1.5"
      onClick={onClick}
      title="Cargue directo sin revisión (super gestión)"
    >
      <DatabaseZap size={14} />
      Cargue directo
    </button>
  );
}
