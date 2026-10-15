import type { EtapaProps } from "../tipos";
import { BotonSuperCargue } from "../comun/BotonesNodo";
import EtapaRaiz from "../comun/EtapaRaiz";
import NodoConcepto from "../comun/NodoConcepto";
import { accionesNodo } from "../nodos";

/**
 * Etapa 2 · Concepto técnico (plan §4): nace con el auto que admite firmado
 * (técnico + fecha de visita). El técnico lo proyecta y carga desde Mis
 * informes; aquí se ve su estado, sus datos y los anexos (los carga el abogado).
 */
export default function ConceptoTecnico({ expediente, etapas, catalogos, setToast, isEditable }: EtapaProps) {
  const nodo = etapas.concepto;
  const puede = accionesNodo(nodo, isEditable);
  return (
    <EtapaRaiz
      nodo={nodo}
      etapa="Concepto técnico"
      isEditable={isEditable}
      descripcion="El concepto técnico nace cuando el abogado carga el auto que admite firmado, con el técnico y la fecha de visita."
      crear={
        puede("super_cargar") ? (
          <BotonSuperCargue
            expedienteId={expediente.id}
            refNodo={{ clase: "concepto", tipo: "etapa2" }}
            titulo={nodo.etiqueta}
            existe={false}
            version={null}
            tieneActo={false}
            setToast={setToast}
          />
        ) : undefined
      }
    >
      <NodoConcepto entorno={{ expediente, catalogos, setToast, isEditable }} nodo={nodo} />
    </EtapaRaiz>
  );
}
