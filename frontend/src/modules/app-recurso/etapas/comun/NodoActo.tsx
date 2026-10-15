import { useState, type ReactNode } from "react";
import { CheckCircle, User } from "lucide-react";
import { EstadoBadge } from "@shared/ui";
import type { NodoEtapa, VinculoInvolucrado } from "../../types";
import type { VarianteActoFinal } from "../formularios/actoFinal";
import { accionesNodo, urlAsignarme, urlVersionFinal, type RefNodo } from "../nodos";
import type { EntornoEtapa } from "../tipos";
import ActoFinalModal from "./ActoFinalModal";
import ActoNodo from "./ActoNodo";
import BotonAsignarme from "./BotonAsignarme";
import { BotonSuperCargue, BotonVersionFinal } from "./BotonesNodo";
import { Dato, SinDato } from "./Dato";
import DocumentosAnexos from "./DocumentosAnexos";
import MotivosBloqueo from "./MotivosBloqueo";
import ProcesoResumen, { EstadoProcesoBadge } from "./ProcesoResumen";
import TarjetaNodo from "./TarjetaNodo";

type Props = {
  entorno: EntornoEtapa;
  nodo: NodoEtapa<unknown>;
  refNodo: RefNodo;
  icono: string;
  /** Datos del acto final que se diligencian al cargarlo. */
  variante?: VarianteActoFinal;
  /** "el auto que admite", "la decisión"... (confirmación de Asignarme). */
  que: string;
  vinculos: VinculoInvolucrado[];
  /** Datos propios de la etapa (debajo del encargado). */
  datos?: ReactNode;
  /** Botones propios del nodo (registrar respuesta, ejecutoria...). */
  acciones?: ReactNode;
  /** Contenido extra al final (sub-procesos anidados). */
  children?: ReactNode;
  anidada?: boolean;
  /** Documentos actuales para "Ver actual" en el cargue directo. */
  actuales?: Record<string, number | null>;
  /** Texto cuando el nodo aún no existe y no está bloqueado. */
  pendiente?: string;
};

/**
 * Nodo con acto administrativo (plan §4-E): asignación del abogado,
 * proyección y revisión (proceso de B), versión final firmada y numerada, y
 * el acto con comunicación / notificaciones. Botones solo por `acciones_disponibles`.
 */
export default function NodoActo({
  entorno,
  nodo,
  refNodo,
  icono,
  variante = "simple",
  que,
  vinculos,
  datos,
  acciones,
  children,
  anidada,
  actuales,
  pendiente = "Pendiente de que un abogado se asigne para diligenciarlo.",
}: Props) {
  const { expediente, setToast, isEditable } = entorno;
  const [cargarFinal, setCargarFinal] = useState(false);
  const puede = accionesNodo(nodo, isEditable);
  const urlAsig = urlAsignarme(expediente.id, refNodo);
  const urlFinal = urlVersionFinal(expediente.id, refNodo);

  const botones = (
    <>
      {acciones}
      {puede("asignarme") && urlAsig && (
        <BotonAsignarme expedienteId={expediente.id} url={urlAsig} que={que} setToast={setToast} />
      )}
      {puede("cargar_version_final") && urlFinal && <BotonVersionFinal onClick={() => setCargarFinal(true)} />}
      {puede("super_cargar") && !(nodo.acto && refNodo.clase.startsWith("aprobacion")) && (
        <BotonSuperCargue
          expedienteId={expediente.id}
          refNodo={refNodo}
          titulo={nodo.etiqueta}
          existe={nodo.id !== null}
          version={nodo.version}
          tieneActo={!!nodo.acto}
          actuales={actuales}
          setToast={setToast}
        />
      )}
    </>
  );

  const estado = nodo.acto ? (
    <EstadoBadge etiqueta="Acto expedido" tono="success" size="md" icono={<CheckCircle size={14} />} />
  ) : nodo.existe ? (
    <EstadoProcesoBadge proceso={nodo.proceso} />
  ) : (
    <EstadoBadge etiqueta={nodo.habilitada ? "Pendiente" : "Bloqueado"} tono={nodo.habilitada ? "neutral" : "warning"} size="md" />
  );

  return (
    <TarjetaNodo
      titulo={nodo.etiqueta}
      subtitulo={nodo.acto ? `Acto No. ${nodo.acto.numerado} del ${nodo.acto.fecha_numerado}` : undefined}
      icono={icono}
      tono={nodo.acto ? "success" : nodo.habilitada ? "info" : "warning"}
      estado={estado}
      acciones={botones}
      anidada={anidada}
    >
      <div className="space-y-4">
        {!nodo.existe && (
          <>
            <MotivosBloqueo motivos={nodo.motivos_bloqueo} />
            {nodo.habilitada && <p className="text-sm text-base-content/60">{pendiente}</p>}
          </>
        )}

        {(nodo.existe || datos) && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {nodo.existe && (
              <Dato icono={<User size={16} />} label="Abogado encargado">
                {nodo.encargado ? (nodo.encargado.nombre ?? `Usuario #${nodo.encargado.id}`) : <SinDato texto="Sin asignar" />}
              </Dato>
            )}
            {datos}
          </div>
        )}

        {!nodo.acto && (
          <ProcesoResumen
            expedienteId={expediente.id}
            proceso={nodo.proceso}
            puedeSubir={puede("subir_version")}
            puedeRevisar={nodo.acciones_disponibles.includes("revisar")}
          />
        )}

        {nodo.acto && (
          <ActoNodo entorno={entorno} acto={nodo.acto} vinculos={vinculos} />
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

      {cargarFinal && urlFinal && (
        <ActoFinalModal
          expedienteId={expediente.id}
          url={urlFinal}
          titulo={nodo.etiqueta}
          variante={variante}
          setToast={setToast}
          onClose={() => setCargarFinal(false)}
        />
      )}
    </TarjetaNodo>
  );
}
