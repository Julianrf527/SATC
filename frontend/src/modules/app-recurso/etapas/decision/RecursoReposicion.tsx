import { useState } from "react";
import { CalendarDays, FileInput, FileText, Hash, Scale } from "lucide-react";
import { formatDate } from "@shared/lib/format";
import { EstadoBadge } from "@shared/ui";
import type { NodoRecurso, VinculoInvolucrado } from "../../types";
import { Dato, SinDato, VerDocumento } from "../comun/Dato";
import NodoActo from "../comun/NodoActo";
import RadicadoModal from "../comun/RadicadoModal";
import { OPCIONES_RESULTADO } from "../formularios/actoFinal";
import { bodyRadicado } from "../formularios/radicado";
import { accionesNodo, urlRegistrarRadicado } from "../nodos";
import type { EntornoEtapa } from "../tipos";

const REF = { clase: "recurso" } as const;

type Props = { entorno: EntornoEtapa; nodo: NodoRecurso; vinculos: VinculoInvolucrado[] };

/**
 * Sub-proceso: recurso de reposición (opcional). Se crea con el radicado y el
 * escrito del usuario; luego un abogado se asigna el acto que lo resuelve
 * (resultado REPONE / CONFIRMA / MODIFICA / ADICIONA) y se notifica.
 */
export default function RecursoReposicion({ entorno, nodo, vinculos }: Props) {
  const { expediente, setToast, isEditable } = entorno;
  const [registrando, setRegistrando] = useState(false);
  const puede = accionesNodo(nodo, isEditable);
  const urlCrear = urlRegistrarRadicado(expediente.id, REF);
  const d = nodo.datos;
  const resultado = OPCIONES_RESULTADO.find((o) => o.value === d.resultado)?.label;

  return (
    <>
      <NodoActo
        entorno={entorno}
        nodo={nodo}
        refNodo={REF}
        icono="bx-revision"
        variante="recurso"
        que="el acto que resuelve el recurso"
        vinculos={vinculos}
        anidada
        actuales={{ radicado: d.doc_recurso_id }}
        pendiente={
          nodo.id === null
            ? "Opcional: el usuario lo radica dentro de los 10 días hábiles siguientes a la notificación de la decisión."
            : "Pendiente de que un abogado se asigne el acto que resuelve el recurso."
        }
        acciones={
          puede("crear_recurso") && urlCrear ? (
            <button type="button" className="btn btn-success btn-sm text-white gap-1.5" onClick={() => setRegistrando(true)}>
              <FileInput size={14} /> Registrar recurso
            </button>
          ) : undefined
        }
        datos={
          nodo.id !== null ? (
            <>
              <Dato icono={<Hash size={16} />} label="Radicado del recurso">
                {d.radicado ?? <SinDato />}
              </Dato>
              <Dato icono={<CalendarDays size={16} />} label="Fecha de radicado">
                {d.fecha_radicado ? formatDate(d.fecha_radicado) : <SinDato />}
              </Dato>
              <Dato icono={<FileText size={16} />} label="Escrito del recurso">
                <VerDocumento fileId={d.doc_recurso_id} />
              </Dato>
              <Dato icono={<Scale size={16} />} label="Resultado">
                {resultado ? <EstadoBadge etiqueta={resultado} tono="info" /> : <SinDato texto="Sin resolver" />}
              </Dato>
            </>
          ) : undefined
        }
      />
      {registrando && urlCrear && (
        <RadicadoModal
          expedienteId={expediente.id}
          titulo="Registrar recurso de reposición"
          documento="Escrito del recurso"
          peticion={(form, id) => ({ url: urlCrear, method: "POST", body: bodyRadicado(form, id) })}
          setToast={setToast}
          onClose={() => setRegistrando(false)}
        />
      )}
    </>
  );
}
