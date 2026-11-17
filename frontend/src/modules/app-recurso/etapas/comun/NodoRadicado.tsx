import type { ReactNode } from "react";
import { CalendarDays, CheckCircle, FileText, Hash } from "lucide-react";
import { formatDate } from "@shared/lib/format";
import { EstadoBadge } from "@shared/ui";
import type { AccionEtapa, NodoRadicado as Nodo } from "../../types";
import { accionesNodo, urlRegistrarRadicado, type RefNodo } from "../nodos";
import type { EntornoEtapa } from "../tipos";
import { BotonSuperCargue } from "./BotonesNodo";
import BotonRegistrarRadicado from "./BotonRegistrarRadicado";
import { Dato, SinDato, VerDocumento } from "./Dato";
import DocumentosAnexos from "./DocumentosAnexos";
import MotivosBloqueo from "./MotivosBloqueo";
import TarjetaNodo from "./TarjetaNodo";

type Props = {
  entorno: EntornoEtapa;
  nodo: Nodo;
  refNodo: RefNodo;
  /** Código de acción que crea la fila (`registrar_planos`, `registrar_informe_usuario`...). */
  accionCrear?: AccionEtapa;
  /** Nombre del documento ("Planos", "Informe del usuario"...). */
  documento: string;
  /** `file_id` del documento (cada nodo lo trae en un campo distinto). */
  fileId: number | null | undefined;
  icono?: string;
  anidada?: boolean;
  /** Sin la sección de anexos (cuando otro nodo muestra la misma fila). */
  sinAnexos?: boolean;
  /** Sin "Cargue directo" (lo ofrece otro nodo de la misma fila). */
  sinSuper?: boolean;
  pendiente?: string;
  children?: ReactNode;
};

/** Documento radicado por el usuario (planos, subsanación, informe): radicado, fecha y PDF. */
export default function NodoRadicado({
  entorno,
  nodo,
  refNodo,
  accionCrear,
  documento,
  fileId,
  icono = "bx-file",
  anidada,
  sinAnexos,
  sinSuper,
  pendiente,
  children,
}: Props) {
  const { expediente, setToast, isEditable } = entorno;
  const puede = accionesNodo(nodo, isEditable);
  const urlCrear = urlRegistrarRadicado(expediente.id, refNodo);

  return (
    <TarjetaNodo
      titulo={nodo.etiqueta}
      icono={icono}
      tono={nodo.existe ? "success" : nodo.habilitada ? "info" : "warning"}
      anidada={anidada}
      estado={
        nodo.existe ? (
          <EstadoBadge etiqueta="Radicado" tono="success" size="md" icono={<CheckCircle size={14} />} />
        ) : (
          <EstadoBadge etiqueta={nodo.habilitada ? "Pendiente" : "Bloqueado"} tono={nodo.habilitada ? "neutral" : "warning"} size="md" />
        )
      }
      acciones={
        <>
          {accionCrear && puede(accionCrear) && urlCrear && (
            <BotonRegistrarRadicado expedienteId={expediente.id} url={urlCrear} documento={documento} setToast={setToast} />
          )}
          {!sinSuper && puede("super_cargar") && (
            <BotonSuperCargue
              expedienteId={expediente.id}
              refNodo={refNodo}
              titulo={nodo.etiqueta}
              existe={nodo.existe}
              version={nodo.version}
              tieneActo={!!nodo.acto}
              actuales={{ radicado: fileId ?? null }}
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
              <p className="text-sm text-base-content/60">{pendiente ?? `Pendiente de registrar: ${documento.toLowerCase()}.`}</p>
            )}
          </>
        )}
        {nodo.existe && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Dato icono={<Hash size={16} />} label="Radicado">
              {nodo.datos.radicado ?? <SinDato />}
            </Dato>
            <Dato icono={<CalendarDays size={16} />} label="Fecha de radicado">
              {nodo.datos.fecha_radicado ? formatDate(nodo.datos.fecha_radicado) : <SinDato />}
            </Dato>
            <Dato icono={<FileText size={16} />} label={documento}>
              <VerDocumento fileId={fileId} />
            </Dato>
          </div>
        )}
        {!sinAnexos && nodo.existe && nodo.id !== null && (nodo.anexos.length > 0 || puede("gestionar_anexos")) && (
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

    </TarjetaNodo>
  );
}
