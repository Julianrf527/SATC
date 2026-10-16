import { useState, type ReactNode } from "react";
import { CalendarDays, CheckCircle, Droplets, FileText, Gauge, User, Users, XCircle } from "lucide-react";
import { formatDate } from "@shared/lib/format";
import { EstadoBadge } from "@shared/ui";
import type { DatosConcepto, NodoConcepto as Nodo } from "../../types";
import { accionesNodo, urlSeleccionarTecnico, urlVersionFinal } from "../nodos";
import type { EntornoEtapa } from "../tipos";
import { BotonSuperCargue, BotonVersionFinal } from "./BotonesNodo";
import ConceptoFinalModal from "./ConceptoFinalModal";
import { Dato, SinDato, VerDocumento } from "./Dato";
import DocumentosAnexos from "./DocumentosAnexos";
import MotivosBloqueo from "./MotivosBloqueo";
import ProcesoResumen, { EstadoProcesoBadge } from "./ProcesoResumen";
import SeleccionarTecnicoModal from "./SeleccionarTecnicoModal";
import TarjetaNodo from "./TarjetaNodo";

type Props = {
  entorno: EntornoEtapa;
  nodo: Nodo;
  anidada?: boolean;
  /** Texto cuando aún no existe y no hay motivo de bloqueo. */
  pendiente?: string;
  children?: ReactNode;
};

const num = (v: number | null | undefined) => (v === null || v === undefined ? <SinDato /> : v.toLocaleString("es-CO"));

/**
 * Concepto técnico (C.4): técnico seleccionado, proyección y revisión,
 * versión firmada con sus datos (caudales, cumple, visita según el tipo).
 */
export default function NodoConcepto({ entorno, nodo, anidada, pendiente, children }: Props) {
  const { expediente, setToast, isEditable } = entorno;
  const [modal, setModal] = useState<"tecnico" | "final" | null>(null);
  const puede = accionesNodo(nodo, isEditable);
  const ref = { clase: "concepto", tipo: nodo.tipo } as const;
  const urlTecnico = urlSeleccionarTecnico(expediente.id, nodo.tipo);
  const urlFinal = urlVersionFinal(expediente.id, ref);
  const d = (nodo.existe ? nodo.datos : {}) as Partial<DatosConcepto>;
  const campos = nodo.campos;
  const muestra = (c: string) => campos.campos.some((x) => x.campo === c);
  const cargado = !!d.doc_concepto_tecnico_id;

  const estado = cargado ? (
    <EstadoBadge etiqueta="Concepto cargado" tono="success" size="md" icono={<CheckCircle size={14} />} />
  ) : nodo.existe ? (
    <EstadoProcesoBadge proceso={nodo.proceso} />
  ) : (
    <EstadoBadge etiqueta={nodo.habilitada ? "Pendiente" : "Bloqueado"} tono={nodo.habilitada ? "neutral" : "warning"} size="md" />
  );

  return (
    <TarjetaNodo
      titulo={nodo.etiqueta}
      subtitulo={cargado ? `Concepto del ${formatDate(d.fecha_aceptacion)}` : undefined}
      icono="bx-book-bookmark"
      tono={cargado ? "success" : nodo.habilitada ? "info" : "warning"}
      estado={estado}
      anidada={anidada}
      acciones={
        <>
          {puede("seleccionar_tecnico") && urlTecnico && (
            <button type="button" className="btn btn-success btn-sm text-white gap-1.5" onClick={() => setModal("tecnico")}>
              <User size={14} /> Seleccionar técnico
            </button>
          )}
          {puede("cargar_version_final") && urlFinal && <BotonVersionFinal onClick={() => setModal("final")} />}
          {puede("super_cargar") && (
            <BotonSuperCargue
              expedienteId={expediente.id}
              refNodo={ref}
              titulo={nodo.etiqueta}
              existe={nodo.existe}
              version={nodo.version}
              tieneActo={false}
              actuales={{ concepto: d.doc_concepto_tecnico_id ?? null }}
              camposConcepto={campos}
              setToast={setToast}
            />
          )}
        </>
      }
    >
      <div className="space-y-4">
        {!nodo.existe && (
          <>
            <MotivosBloqueo motivos={nodo.motivos_bloqueo} />
            {nodo.habilitada && (
              <p className="text-sm text-base-content/60">
                {pendiente ?? "Pendiente de que el abogado seleccione el técnico encargado."}
              </p>
            )}
          </>
        )}

        {nodo.existe && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Dato icono={<User size={16} />} label="Técnico encargado">
              {nodo.tecnico ? (nodo.tecnico.nombre ?? `Usuario #${nodo.tecnico.id}`) : <SinDato texto="Sin asignar" />}
            </Dato>
            {(muestra("fecha_visita_tecnica") || d.fecha_visita_tecnica) && (
              <Dato icono={<CalendarDays size={16} />} label="Fecha de visita">
                {d.fecha_visita_tecnica ? formatDate(d.fecha_visita_tecnica) : <SinDato />}
              </Dato>
            )}
            <Dato icono={<CalendarDays size={16} />} label="Fecha del concepto" destacado={cargado}>
              {d.fecha_aceptacion ? formatDate(d.fecha_aceptacion) : <SinDato />}
            </Dato>
            <Dato icono={<FileText size={16} />} label="Concepto firmado">
              <VerDocumento fileId={d.doc_concepto_tecnico_id} texto="Ver concepto" />
            </Dato>
            {muestra("caudal_fuente") && (
              <>
                <Dato icono={<Droplets size={16} />} label="Caudal fuente (L/s)">{num(d.caudal_fuente)}</Dato>
                <Dato icono={<Droplets size={16} />} label="Caudal disponible (L/s)">{num(d.caudal_disponible)}</Dato>
                <Dato icono={<Gauge size={16} />} label="Caudal otorgado (L/s)">{num(d.caudal_otorgado)}</Dato>
                <Dato icono={<Users size={16} />} label="Número de usuarios">{num(d.num_usuarios)}</Dato>
              </>
            )}
            {muestra("cumple") && (
              <Dato icono={d.cumple === false ? <XCircle size={16} /> : <CheckCircle size={16} />} label="Resultado">
                {d.cumple === null || d.cumple === undefined ? (
                  <SinDato />
                ) : (
                  <EstadoBadge etiqueta={d.cumple ? "Cumple" : "No cumple"} tono={d.cumple ? "success" : "error"} />
                )}
              </Dato>
            )}
          </div>
        )}

        {!cargado && (
          <ProcesoResumen
            expedienteId={expediente.id}
            proceso={nodo.proceso}
            puedeSubir={puede("subir_version")}
            puedeRevisar={nodo.acciones_disponibles.includes("revisar")}
          />
        )}

        {nodo.existe && nodo.id !== null && (nodo.anexos.length > 0 || puede("gestionar_anexos")) && (
          <DocumentosAnexos
            expedienteId={expediente.id}
            etapaTipo={nodo.etapa_tipo}
            etapaRefId={nodo.id}
            anexos={nodo.anexos}
            puedeGestionar={puede("gestionar_anexos")}
            setToast={setToast}
          />
        )}

        {children}
      </div>

      {modal === "tecnico" && urlTecnico && (
        <SeleccionarTecnicoModal
          expedienteId={expediente.id}
          url={urlTecnico}
          titulo={nodo.etiqueta}
          setToast={setToast}
          onClose={() => setModal(null)}
        />
      )}
      {modal === "final" && urlFinal && (
        <ConceptoFinalModal
          expedienteId={expediente.id}
          url={urlFinal}
          campos={campos}
          titulo={nodo.etiqueta}
          datos={d}
          setToast={setToast}
          onClose={() => setModal(null)}
        />
      )}
    </TarjetaNodo>
  );
}
