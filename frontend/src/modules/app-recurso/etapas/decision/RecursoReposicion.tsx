import { useState } from "react";
import { CalendarDays, FileInput, FileText, FlaskConical, Hash, Pencil, Scale } from "lucide-react";
import { formatDate } from "@shared/lib/format";
import { EstadoBadge } from "@shared/ui";
import type { NodoPracticaPruebas, NodoRecurso, VinculoInvolucrado } from "../../types";
import { CampoSiNo } from "../comun/campos/Campos";
import { Dato, SinDato, VerDocumento } from "../comun/Dato";
import NodoActo from "../comun/NodoActo";
import NodoConcepto from "../comun/NodoConcepto";
import RadicadoModal from "../comun/RadicadoModal";
import { OPCIONES_RESULTADO } from "../formularios/actoFinal";
import { bodyRadicado } from "../formularios/radicado";
import { validarRespuestaPruebas } from "../formularios/requierePruebas";
import { accionesNodo, urlRegistrarRadicado } from "../nodos";
import type { EntornoEtapa } from "../tipos";
import RequierePruebasModal from "./RequierePruebasModal";

const REF = { clase: "recurso" } as const;
const REF_PRUEBAS = { clase: "pruebas" } as const;

type Props = { entorno: EntornoEtapa; nodo: NodoRecurso; vinculos: VinculoInvolucrado[] };

/**
 * Sub-proceso: recurso de reposición (opcional). Se crea con el radicado, el
 * escrito del usuario y la respuesta a «¿Requiere práctica de pruebas?».
 * Sin pruebas, un abogado se asigna directo el acto que lo resuelve. Con
 * pruebas, antes van el auto que admite y decreta práctica de pruebas (con
 * técnico y fecha de visita) y su concepto técnico; con el concepto firmado
 * se habilita el acto que resuelve (REPONE / CONFIRMA / MODIFICA / ADICIONA).
 */
export default function RecursoReposicion({ entorno, nodo, vinculos }: Props) {
  const { expediente, setToast, isEditable } = entorno;
  const [modal, setModal] = useState<"registrar" | "pruebas" | null>(null);
  const [requiere, setRequiere] = useState<boolean | null>(null);
  const puede = accionesNodo(nodo, isEditable);
  const urlCrear = urlRegistrarRadicado(expediente.id, REF);
  const d = nodo.datos;
  const resultado = OPCIONES_RESULTADO.find((o) => o.value === d.resultado)?.label;

  const abrirRegistro = () => {
    setRequiere(null);
    setModal("registrar");
  };

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
        sinAnexos
        actuales={{ radicado: d.doc_recurso_id }}
        pendiente={
          nodo.id === null
            ? "Opcional: el usuario lo radica dentro de los 10 días hábiles siguientes a la notificación de la decisión."
            : "Pendiente de que un abogado se asigne el acto que resuelve el recurso."
        }
        acciones={
          <>
            {puede("crear_recurso") && urlCrear && (
              <button type="button" className="btn btn-success btn-sm text-white gap-1.5" onClick={abrirRegistro}>
                <FileInput size={14} /> Registrar recurso
              </button>
            )}
            {puede("editar_requiere_pruebas") && nodo.version !== null && (
              <button type="button" className="btn btn-outline btn-sm gap-1.5" onClick={() => setModal("pruebas")}>
                <Pencil size={14} /> Práctica de pruebas
              </button>
            )}
          </>
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
              <Dato icono={<FlaskConical size={16} />} label="¿Requiere práctica de pruebas?">
                <EstadoBadge etiqueta={d.requiere_pruebas ? "Sí" : "No"} tono={d.requiere_pruebas ? "info" : "neutral"} />
              </Dato>
              <Dato icono={<Scale size={16} />} label="Resultado">
                {resultado ? <EstadoBadge etiqueta={resultado} tono="info" /> : <SinDato texto="Sin resolver" />}
              </Dato>
            </>
          ) : undefined
        }
        previo={nodo.pruebas && <PracticaPruebas entorno={entorno} nodo={nodo.pruebas} vinculos={vinculos} />}
      />

      {modal === "registrar" && urlCrear && (
        <RadicadoModal
          expedienteId={expediente.id}
          titulo="Registrar recurso de reposición"
          documento="Escrito del recurso"
          peticion={(form, id) => ({
            url: urlCrear,
            method: "POST",
            body: { ...bodyRadicado(form, id), requiere_pruebas: requiere },
          })}
          validarExtra={() => validarRespuestaPruebas(requiere)}
          setToast={setToast}
          onClose={() => setModal(null)}
        >
          <CampoSiNo etiqueta="¿Requiere práctica de pruebas?" valor={requiere} onChange={setRequiere} requerido />
          <p className="text-xs text-base-content/60">
            Si requiere, antes del acto que resuelve el recurso se emite el auto que admite y decreta práctica de pruebas
            y se carga su concepto técnico. Se puede cambiar después.
          </p>
        </RadicadoModal>
      )}
      {modal === "pruebas" && nodo.version !== null && (
        <RequierePruebasModal
          expedienteId={expediente.id}
          version={nodo.version}
          actual={!!d.requiere_pruebas}
          avisoEliminar={nodo.aviso_eliminar_pruebas}
          setToast={setToast}
          onClose={() => setModal(null)}
        />
      )}
    </>
  );
}

/** Auto que admite y decreta práctica de pruebas (solo se comunica) + concepto técnico de pruebas. */
function PracticaPruebas({ entorno, nodo, vinculos }: { entorno: EntornoEtapa; nodo: NodoPracticaPruebas; vinculos: VinculoInvolucrado[] }) {
  return (
    <NodoActo
      entorno={entorno}
      nodo={nodo}
      refNodo={REF_PRUEBAS}
      icono="bx-test-tube"
      variante="pruebas"
      que="el auto que admite y decreta práctica de pruebas"
      vinculos={vinculos}
      anidada
      sinAnexos
      pendiente="Pendiente de que un abogado se asigne el auto que admite y decreta práctica de pruebas."
    >
      <NodoConcepto
        entorno={entorno}
        nodo={nodo.concepto}
        anidada
        sinAnexos
        pendiente="Nace al cargar el auto firmado con el técnico y la fecha de visita."
      />
    </NodoActo>
  );
}
