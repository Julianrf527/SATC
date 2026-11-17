import { useState } from "react";
import { CalendarDays, FileInput, FileText, Hash } from "lucide-react";
import { RECURSO_ENDPOINTS } from "@shared/lib/api";
import { formatDate } from "@shared/lib/format";
import type { EtapaProps } from "../tipos";
import { vinculosNotificables } from "../comun/actoFeature";
import BotonAsignarme from "../comun/BotonAsignarme";
import { BotonSuperCargue } from "../comun/BotonesNodo";
import { Dato, SinDato, VerDocumento } from "../comun/Dato";
import EtapaRaiz from "../comun/EtapaRaiz";
import NodoActo from "../comun/NodoActo";
import NodoConcepto from "../comun/NodoConcepto";
import RadicadoModal from "../comun/RadicadoModal";
import { bodyRespuestaRequerimiento } from "../formularios/radicado";
import { accionesNodo, urlAsignarme } from "../nodos";

const REF = { clase: "requerimiento", ambito: "etapa3" } as const;

/**
 * Etapa 3 · Requerimiento (opcional, plan §4): acto con revisión jurídica,
 * notificación, respuesta del usuario (radicado + PDF) y, si hay que
 * reevaluarla, el concepto técnico adicional (sin visita).
 */
export default function Requerimiento({ expediente, etapas, catalogos, setToast, isEditable }: EtapaProps) {
  const [respuesta, setRespuesta] = useState(false);
  const nodo = etapas.requerimiento;
  const entorno = { expediente, catalogos, setToast, isEditable };
  const puede = accionesNodo(nodo, isEditable);
  const urlAsig = urlAsignarme(expediente.id, REF);
  const d = nodo.datos;

  return (
    <EtapaRaiz
      nodo={nodo}
      etapa="Requerimiento"
      isEditable={isEditable}
      descripcion="Es opcional: sale cuando el concepto permite otorgar pero falta algo. Si no falta nada, se pasa directo a la decisión."
      crear={
        <>
          {puede("asignarme") && urlAsig && (
            <BotonAsignarme expedienteId={expediente.id} url={urlAsig} que="el requerimiento" setToast={setToast} grande />
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
          icono="bx-error-alt"
          que="el requerimiento"
          vinculos={vinculosNotificables(expediente.involucrados, etapas.terceros)}
          actuales={{ respuesta: d.doc_oficio_entrada_id }}
          acciones={
            puede("registrar_respuesta") && nodo.version !== null ? (
              <button type="button" className="btn btn-outline btn-sm gap-1.5" onClick={() => setRespuesta(true)}>
                <FileInput size={14} /> {d.doc_oficio_entrada_id ? "Cambiar respuesta" : "Registrar respuesta"}
              </button>
            ) : undefined
          }
          datos={
            nodo.acto ? (
              <>
                <Dato icono={<Hash size={16} />} label="Radicado de la respuesta">
                  {d.radicado_oficio_entrada ?? <SinDato texto="Sin respuesta" />}
                </Dato>
                <Dato icono={<CalendarDays size={16} />} label="Fecha de la respuesta">
                  {d.fecha_oficio_entrada ? formatDate(d.fecha_oficio_entrada) : <SinDato />}
                </Dato>
                <Dato icono={<FileText size={16} />} label="Oficio de respuesta">
                  <VerDocumento fileId={d.doc_oficio_entrada_id} />
                </Dato>
              </>
            ) : undefined
          }
        />

        <NodoConcepto
          entorno={entorno}
          nodo={nodo.concepto_adicional}
          pendiente="Opcional: solo si la respuesta del usuario hay que reevaluarla. El abogado del requerimiento selecciona el técnico."
        />
      </div>

      {respuesta && nodo.version !== null && (
        <RadicadoModal
          expedienteId={expediente.id}
          titulo="Respuesta del usuario al requerimiento"
          documento="Oficio de respuesta"
          peticion={(form, id) => ({
            url: RECURSO_ENDPOINTS.RECURSO_ETAPA_ACCION(expediente.id, "requerimientos/etapa3/respuesta"),
            method: "PUT",
            body: bodyRespuestaRequerimiento(form, id, nodo.version as number),
          })}
          setToast={setToast}
          onClose={() => setRespuesta(false)}
        />
      )}
    </EtapaRaiz>
  );
}
