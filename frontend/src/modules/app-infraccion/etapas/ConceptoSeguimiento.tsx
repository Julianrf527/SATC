import type { ComponentProps } from "react";
import Concepto from "./Concepto";

/**
 * Etapa 5 · Acoger Concepto · Seguimiento: la misma etapa de acoger concepto
 * (tipo de acogida, término, oficio, solicitud de información y acto con su
 * proceso de revisión) para la visita de seguimiento. Se habilita cuando el
 * informe técnico de SEGUIMIENTO está aceptado.
 */
export default function ConceptoSeguimiento(props: Omit<ComponentProps<typeof Concepto>, "instancia">) {
  return <Concepto {...props} instancia="SEGUIMIENTO" />;
}
