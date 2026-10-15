import { useState } from "react";
import { CalendarCheck, Calculator, Gavel } from "lucide-react";
import { formatDate } from "@shared/lib/format";
import { EstadoBadge } from "@shared/ui";
import type { EtapaProps } from "../tipos";
import { vinculosNotificables } from "../comun/actoFeature";
import BotonAsignarme from "../comun/BotonAsignarme";
import { BotonSuperCargue } from "../comun/BotonesNodo";
import { Dato, SinDato } from "../comun/Dato";
import EtapaRaiz from "../comun/EtapaRaiz";
import NodoActo from "../comun/NodoActo";
import { OPCIONES_DECISION } from "../formularios/actoFinal";
import { accionesNodo, urlAsignarme } from "../nodos";
import EjecutoriaModal from "./EjecutoriaModal";
import RecursoReposicion from "./RecursoReposicion";

const REF = { clase: "decision" } as const;
const TONO_DECISION = { OTORGADA: "success", NEGADA: "error", DESISTIDA: "neutral" } as const;

/**
 * Etapa 4 · Decisión (plan §4): acto con revisión de líder jurídico → líder
 * del proyecto y asesora de subdirección; versión firmada con la decisión y
 * si exige memorias; notificación; fecha de ejecutoria; recurso de reposición.
 */
export default function Decision({ expediente, etapas, catalogos, setToast, isEditable }: EtapaProps) {
  const [ejecutoria, setEjecutoria] = useState(false);
  const nodo = etapas.decision;
  const entorno = { expediente, catalogos, setToast, isEditable };
  const puede = accionesNodo(nodo, isEditable);
  const urlAsig = urlAsignarme(expediente.id, REF);
  const vinculos = vinculosNotificables(expediente.involucrados, etapas.terceros);
  const d = nodo.datos;
  const decision = OPCIONES_DECISION.find((o) => o.value === d.decision);

  return (
    <EtapaRaiz
      nodo={nodo}
      etapa="Decisión"
      isEditable={isEditable}
      descripcion="Un abogado se asigna la decisión del proceso (otorgada, negada o desistida) para proyectarla y enviarla a revisión."
      crear={
        <>
          {puede("asignarme") && urlAsig && (
            <BotonAsignarme expedienteId={expediente.id} url={urlAsig} que="la decisión" setToast={setToast} grande />
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
          icono="bx-check-shield"
          variante="decision"
          que="la decisión"
          vinculos={vinculos}
          acciones={
            puede("registrar_ejecutoria") && nodo.version !== null ? (
              <button type="button" className="btn btn-outline btn-sm gap-1.5" onClick={() => setEjecutoria(true)}>
                <CalendarCheck size={14} /> Fecha de ejecutoria
              </button>
            ) : undefined
          }
          datos={
            nodo.acto ? (
              <>
                <Dato icono={<Gavel size={16} />} label="Decisión">
                  {decision ? <EstadoBadge etiqueta={decision.label} tono={TONO_DECISION[decision.value]} /> : <SinDato />}
                </Dato>
                {d.decision === "OTORGADA" && (
                  <Dato icono={<Calculator size={16} />} label="Exige memorias de cálculo">
                    {d.requiere_memorias === null ? <SinDato /> : d.requiere_memorias ? "Sí (planos)" : "No (medidor o llave)"}
                  </Dato>
                )}
                <Dato icono={<CalendarCheck size={16} />} label="Fecha de ejecutoria" destacado={!!d.fecha_ejecutoria}>
                  {d.fecha_ejecutoria ? formatDate(d.fecha_ejecutoria) : <SinDato />}
                </Dato>
              </>
            ) : undefined
          }
        />

        <RecursoReposicion entorno={entorno} nodo={nodo.recurso} vinculos={vinculos} />
      </div>

      {ejecutoria && nodo.version !== null && (
        <EjecutoriaModal
          expedienteId={expediente.id}
          version={nodo.version}
          actual={d.fecha_ejecutoria}
          setToast={setToast}
          onClose={() => setEjecutoria(false)}
        />
      )}
    </EtapaRaiz>
  );
}
