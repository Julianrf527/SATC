import type { EtapaProps } from "../tipos";
import { vinculosNotificables } from "../comun/actoFeature";
import TerceroCard from "./TerceroCard";
import TercerosExpediente from "./TercerosExpediente";

/**
 * Transversal · Tercero interviniente (plan §4): persona que se opone al
 * permiso. Arriba, la tarjeta de personas vinculadas (como Solicitantes);
 * debajo, una tarjeta por tercero con el acto que lo reconoce (solo se
 * comunica, no se notifica).
 */
export default function TerceroInterviniente({ expediente, etapas, catalogos, setToast, isEditable }: EtapaProps) {
  const entorno = { expediente, catalogos, setToast, isEditable };
  const terceros = etapas.terceros;
  const puedeVincular = isEditable && etapas.acciones_disponibles.includes("vincular_tercero");
  const vinculos = vinculosNotificables(expediente.involucrados, terceros);

  return (
    <div className="space-y-6">
      <TercerosExpediente
        expediente={expediente}
        terceros={terceros}
        puedeVincular={puedeVincular}
        setToast={setToast}
        isEditable={isEditable}
      />

      {terceros.map((t) => (
        <TerceroCard key={t.id} entorno={entorno} tercero={t} vinculos={vinculos} />
      ))}
    </div>
  );
}
