import type { NodoTercero, VinculoInvolucrado } from "../../types";
import NodoActo from "../comun/NodoActo";
import type { EntornoEtapa } from "../tipos";
import { nombrePersona } from "../involucrados/personaForm";

type Props = { entorno: EntornoEtapa; tercero: NodoTercero; vinculos: VinculoInvolucrado[] };

/**
 * Acto que reconoce a un tercero interviniente (C.10): asignarme → revisión →
 * versión final → comunicación (no se notifica). No lleva anexos. Los datos
 * de la persona están arriba, en la tarjeta "Terceros intervinientes".
 */
export default function TerceroCard({ entorno, tercero, vinculos }: Props) {
  const nombre = nombrePersona(tercero.involucrado);
  // El vínculo es un nodo del árbol sin `datos` ni técnico.
  const nodo = { ...tercero, etiqueta: `Acto que reconoce a ${nombre}`, datos: {}, tecnico: null };

  return (
    <NodoActo
      entorno={entorno}
      nodo={nodo}
      refNodo={{ clase: "tercero", vinculoId: tercero.id }}
      icono="bx-user-voice"
      que={`el acto que reconoce a ${nombre}`}
      vinculos={vinculos}
      pendiente="Pendiente de que un abogado se asigne el acto que reconoce al tercero."
    />
  );
}
