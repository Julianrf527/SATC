import type { EtapaProps } from "../tipos";
import { vinculosNotificables } from "../comun/actoFeature";
import { BotonSuperCargue } from "../comun/BotonesNodo";
import BotonRegistrarRadicado from "../comun/BotonRegistrarRadicado";
import EtapaRaiz from "../comun/EtapaRaiz";
import NodoActo from "../comun/NodoActo";
import NodoConcepto from "../comun/NodoConcepto";
import NodoRadicado from "../comun/NodoRadicado";
import { accionesNodo, urlRegistrarRadicado } from "../nodos";

const REF = { clase: "memorias" } as const;

/**
 * Etapa 5 · Memorias de cálculo (opcional, plan §4): planos radicados →
 * concepto (cumple / no cumple) → si no cumple, requerimiento, subsanación y
 * su concepto → acto que aprueba las memorias. Cada paso es una tarjeta, en
 * el orden del ciclo.
 */
export default function MemoriasCalculo({ expediente, etapas, catalogos, setToast, isEditable }: EtapaProps) {
  const nodo = etapas.memorias;
  const entorno = { expediente, catalogos, setToast, isEditable };
  const puede = accionesNodo(nodo, isEditable);
  const urlPlanos = urlRegistrarRadicado(expediente.id, REF);
  const vinculos = vinculosNotificables(expediente.involucrados, etapas.terceros);

  return (
    <EtapaRaiz
      nodo={nodo}
      etapa="Memorias de cálculo"
      isEditable={isEditable}
      descripcion="Solo aplica si la decisión es otorgada y exige planos. Empieza con el radicado de los planos del usuario."
      crear={
        <>
          {puede("registrar_planos") && urlPlanos && (
            <BotonRegistrarRadicado expedienteId={expediente.id} url={urlPlanos} documento="Planos" setToast={setToast} grande />
          )}
          {puede("super_cargar") && (
            <BotonSuperCargue
              expedienteId={expediente.id}
              refNodo={REF}
              titulo={nodo.etiqueta}
              existe={false}
              version={null}
              tieneActo={false}
              setToast={setToast}
            />
          )}
        </>
      }
    >
      <div className="space-y-6">
        <NodoRadicado
          entorno={entorno}
          nodo={{ ...nodo, etiqueta: "Planos del usuario" }}
          refNodo={REF}
          documento="Planos"
          fileId={nodo.datos.doc_planos_id}
          icono="bx-calculator"
        />
        <NodoConcepto entorno={entorno} nodo={nodo.concepto} />
        <NodoActo
          entorno={entorno}
          nodo={nodo.requerimiento}
          refNodo={{ clase: "requerimiento", ambito: "memorias" }}
          icono="bx-error-alt"
          que="el requerimiento de memorias"
          vinculos={vinculos}
          pendiente="Solo si el concepto dice que no cumple. Un abogado se lo asigna."
        />
        <NodoRadicado
          entorno={entorno}
          nodo={nodo.subsanacion}
          refNodo={{ clase: "subsanacion" }}
          accionCrear="registrar_subsanacion"
          documento="Planos ajustados"
          fileId={nodo.subsanacion.datos.doc_planos_ajustados_id}
          pendiente="Después del requerimiento firmado, el usuario radica los planos ajustados."
        />
        <NodoConcepto entorno={entorno} nodo={nodo.subsanacion.concepto} />
        <NodoActo
          entorno={entorno}
          nodo={nodo.aprobacion}
          refNodo={{ clase: "aprobacion_memorias" }}
          icono="bx-badge-check"
          que="el acto que aprueba las memorias"
          vinculos={vinculos}
        />
      </div>
    </EtapaRaiz>
  );
}
