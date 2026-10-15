import { useState } from "react";
import { FileUp, Landmark, Megaphone, Stamp } from "lucide-react";
import type { EtapaProps } from "../tipos";
import { vinculosNotificables } from "../comun/actoFeature";
import BotonAsignarme from "../comun/BotonAsignarme";
import { BotonSuperCargue } from "../comun/BotonesNodo";
import { Dato, VerDocumento } from "../comun/Dato";
import EtapaRaiz from "../comun/EtapaRaiz";
import NodoActo from "../comun/NodoActo";
import { accionesNodo, urlAsignarme } from "../nodos";
import DocumentosAdmiteModal from "./DocumentosAdmiteModal";
import { documentosPermitidos } from "./documentosAdmite";

const REF = { clase: "admite" } as const;

/**
 * Etapa 1 · Auto que admite (plan §4): asignación del abogado, proyección y
 * revisión, versión firmada con técnico y fecha de visita (nace la etapa 2),
 * comunicación / notificaciones, oficio a la Alcaldía, fijación del aviso y
 * constancia de fijación.
 */
export default function AutoAdmite({ expediente, etapas, catalogos, setToast, isEditable }: EtapaProps) {
  const [documentos, setDocumentos] = useState(false);
  const nodo = etapas.admite;
  const entorno = { expediente, catalogos, setToast, isEditable };
  const puede = accionesNodo(nodo, isEditable);
  const permitidos = documentosPermitidos(puede);
  const urlAsig = urlAsignarme(expediente.id, REF);
  const actuales = {
    oficio: nodo.datos.doc_oficio_alcaldia_id,
    fijacion: nodo.datos.doc_fijacion_aviso_id,
    constancia: nodo.datos.doc_constancia_fijacion_aviso_id,
  };

  return (
    <EtapaRaiz
      nodo={nodo}
      etapa="Auto que admite"
      isEditable={isEditable}
      descripcion="Un abogado se asigna el auto para proyectarlo y enviarlo a revisión jurídica."
      crear={
        <>
          {puede("asignarme") && urlAsig && (
            <BotonAsignarme expedienteId={expediente.id} url={urlAsig} que="el auto que admite" setToast={setToast} grande />
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
        <NodoActo
          entorno={entorno}
          nodo={nodo}
          refNodo={REF}
          icono="bx-file"
          variante="admite"
          que="el auto que admite"
          vinculos={vinculosNotificables(expediente.involucrados, etapas.terceros)}
          actuales={actuales}
          acciones={
            permitidos.length > 0 && nodo.version !== null ? (
              <button type="button" className="btn btn-outline btn-sm gap-1.5" onClick={() => setDocumentos(true)}>
                <FileUp size={14} /> Cargar documentos
              </button>
            ) : undefined
          }
          datos={
            nodo.acto ? (
              <>
                <Dato icono={<Landmark size={16} />} label="Oficio a la Alcaldía">
                  <VerDocumento fileId={nodo.datos.doc_oficio_alcaldia_id} />
                </Dato>
                <Dato icono={<Megaphone size={16} />} label="Fijación del aviso">
                  <VerDocumento fileId={nodo.datos.doc_fijacion_aviso_id} />
                </Dato>
                <Dato icono={<Stamp size={16} />} label="Constancia de fijación" destacado={!!nodo.datos.doc_constancia_fijacion_aviso_id}>
                  <VerDocumento fileId={nodo.datos.doc_constancia_fijacion_aviso_id} />
                </Dato>
              </>
            ) : undefined
          }
        />
      </div>

      {documentos && nodo.version !== null && (
        <DocumentosAdmiteModal
          expedienteId={expediente.id}
          version={nodo.version}
          datos={nodo.datos}
          permitidos={permitidos}
          setToast={setToast}
          onClose={() => setDocumentos(false)}
        />
      )}
    </EtapaRaiz>
  );
}
