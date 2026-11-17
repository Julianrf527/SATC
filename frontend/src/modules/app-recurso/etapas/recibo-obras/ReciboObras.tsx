import type { EtapaProps } from "../tipos";
import { vinculosNotificables } from "../comun/actoFeature";
import { BotonSuperCargue } from "../comun/BotonesNodo";
import DocumentosAnexos from "../comun/DocumentosAnexos";
import BotonRegistrarRadicado from "../comun/BotonRegistrarRadicado";
import EtapaRaiz from "../comun/EtapaRaiz";
import NodoActo from "../comun/NodoActo";
import NodoConcepto from "../comun/NodoConcepto";
import NodoRadicado from "../comun/NodoRadicado";
import { accionesNodo, urlRegistrarRadicado } from "../nodos";

const REF = { clase: "obras" } as const;

/**
 * Etapa 6 · Recibo a satisfacción de obras (plan §4): informe del usuario →
 * concepto con visita (cumple / no cumple) → si no cumple, requerimiento,
 * nuevo informe y segundo concepto → acto que aprueba la obra.
 */
export default function ReciboObras({ expediente, etapas, catalogos, setToast, isEditable }: EtapaProps) {
  const nodo = etapas.obras;
  const entorno = { expediente, catalogos, setToast, isEditable };
  const puede = accionesNodo(nodo, isEditable);
  const urlInforme = urlRegistrarRadicado(expediente.id, REF);
  const vinculos = vinculosNotificables(expediente.involucrados, etapas.terceros);
  const informe = nodo.informe;
  const puedeInforme = accionesNodo(informe, isEditable);

  return (
    <EtapaRaiz
      nodo={nodo}
      etapa="Recibo de obras"
      isEditable={isEditable}
      descripcion="Aplica cuando la decisión es otorgada. Empieza con el informe del usuario: construyó la obra o instaló el medidor o la llave."
      crear={
        <>
          {puede("registrar_informe_usuario") && urlInforme && (
            <BotonRegistrarRadicado
              expedienteId={expediente.id}
              url={urlInforme}
              documento="Informe del usuario"
              setToast={setToast}
              grande
            />
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
        {/* El informe y la fila de obras se muestran juntos: cargue directo en esta tarjeta y, por separado,
            los anexos de la etapa (fila de obras) y los del informe (nodo `informe`, etapa_tipo informe_usuario). */}
        <NodoRadicado
          entorno={entorno}
          nodo={{ ...nodo, etiqueta: "Informe del usuario", datos: { ...nodo.informe.datos, ...nodo.datos } }}
          refNodo={REF}
          documento="Informe del usuario"
          fileId={nodo.datos.doc_informe_usuario_id ?? nodo.informe.datos.doc_informe_usuario_id}
          icono="bx-wrench"
        >
          {informe.existe && informe.id !== null && (informe.anexos.length > 0 || puedeInforme("gestionar_anexos")) && (
            <DocumentosAnexos
              expedienteId={expediente.id}
              etapaTipo={informe.etapa_tipo}
              etapaRefId={informe.id}
              anexos={informe.anexos}
              puedeGestionar={puedeInforme("gestionar_anexos")}
              setToast={setToast}
              titulo="Documentos anexos del informe del usuario"
            />
          )}
        </NodoRadicado>
        <NodoConcepto entorno={entorno} nodo={nodo.concepto} />
        <NodoActo
          entorno={entorno}
          nodo={nodo.requerimiento}
          refNodo={{ clase: "requerimiento", ambito: "obras" }}
          icono="bx-error-alt"
          que="el requerimiento de obras"
          vinculos={vinculos}
          pendiente="Solo si el concepto dice que no cumple. Un abogado se lo asigna."
        />
        <NodoRadicado
          entorno={entorno}
          nodo={nodo.nuevo_informe}
          refNodo={{ clase: "nuevo_informe" }}
          accionCrear="registrar_nuevo_informe"
          documento="Nuevo informe"
          fileId={nodo.nuevo_informe.datos.doc_informe_usuario_id}
          pendiente="Después del requerimiento firmado, el usuario radica un nuevo informe."
        />
        <NodoConcepto entorno={entorno} nodo={nodo.concepto_segundo} />
        <NodoActo
          entorno={entorno}
          nodo={nodo.aprobacion}
          refNodo={{ clase: "aprobacion_obras" }}
          icono="bx-badge-check"
          que="el acto que aprueba la obra"
          vinculos={vinculos}
        />
      </div>
    </EtapaRaiz>
  );
}
