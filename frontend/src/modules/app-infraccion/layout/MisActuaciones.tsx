import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { ArrowRight, ClipboardList, Leaf } from "lucide-react";
import { usePrecargarProceso } from "@features/proceso-revision";
import { actoAdapter, useMisActuacionesQuery } from "../api/actos";
import { informeAdapter } from "../api/informeAdapter";
import ProcesoActoModal from "../etapas/actos/ProcesoActoModal";
import ProcesoInformeModal from "../informe-tecnico/ProcesoInformeModal";
import MatrizRecursosAfectadosModal from "../modal/MatrizRecursosAfectadosModal";
import type { Actuacion } from "../types";
import { FILTROS_MIS_ACTUACIONES, filtrarActuaciones, opcionesEstado, pestanaDeActuacion } from "./mis-actuaciones/filtros";
import MisActuacionesFiltros from "./mis-actuaciones/MisActuacionesFiltros";
import MisActuacionesTabla from "./mis-actuaciones/MisActuacionesTabla";
import { useIrAlExpediente } from "./mis-actuaciones/useIrAlExpediente";

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

type Abierto = { clave: string; categoria: Actuacion["categoria"]; procesoId: number };

/** Lo que manda una notificación: informe (`informeIdToSelect`) o proceso de acto (`actoProcesoIdToSelect`). */
function destinoNotificacion(state: unknown): { clave: string } | null {
  const s = state as { informeIdToSelect?: string; actoProcesoIdToSelect?: string } | null;
  const informe = Number(s?.informeIdToSelect);
  if (Number.isInteger(informe) && informe > 0) return { clave: `informe-${informe}` };
  const acto = Number(s?.actoProcesoIdToSelect);
  if (Number.isInteger(acto) && acto > 0) return { clave: `acto-${acto}` };
  return null;
}

/**
 * "Mis actuaciones" de infracciones (antes Mis informes), como la de recurso:
 * informes técnicos (técnico / líder técnico) y actos administrativos
 * (encargado / líder de proyecto) en una sola tabla. La versión final de un
 * acto se carga en su etapa ("Ver en el expediente" / "Ir a la etapa" en el
 * modal del proceso, como recurso).
 */
export default function MisActuaciones({ setToast }: Props) {
  const precargarInforme = usePrecargarProceso(informeAdapter);
  const precargarActo = usePrecargarProceso(actoAdapter);
  const { puedeIr, ir } = useIrAlExpediente();
  const location = useLocation();
  const { data, isPending, isFetching, isError, refetch } = useMisActuacionesQuery();
  const actuaciones = useMemo(() => data?.actuaciones ?? [], [data]);

  const [filtros, setFiltros] = useState(FILTROS_MIS_ACTUACIONES);
  const [abierto, setAbierto] = useState<Abierto | null>(null);
  const [matrizInformeId, setMatrizInformeId] = useState<number | null>(null);
  const [pendiente, setPendiente] = useState<{ clave: string } | null>(null);

  // Notificación: se guarda el destino y se abre cuando llegue la lista.
  useEffect(() => {
    const destino = destinoNotificacion(location.state);
    if (destino !== null) {
      setPendiente(destino);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  useEffect(() => {
    if (pendiente === null || isPending) return;
    const fila = actuaciones.find((a) => a.clave === pendiente.clave);
    if (fila?.proceso_id != null) {
      setAbierto({ clave: fila.clave, categoria: fila.categoria, procesoId: fila.proceso_id });
    } else {
      setToast({
        id: Date.now(),
        message: fila ? "No tiene un proceso de revisión vigente" : "Ya no aparece entre tus actuaciones",
        type: "error",
      });
    }
    setPendiente(null);
  }, [pendiente, isPending, actuaciones, setToast]);

  const filtrados = useMemo(() => filtrarActuaciones(actuaciones, filtros), [actuaciones, filtros]);
  const estados = useMemo(() => opcionesEstado(actuaciones), [actuaciones]);
  // Fila fresca (se re-lee tras invalidar): decide el botón "Editar matriz".
  const filaAbierta = actuaciones.find((a) => a.clave === abierto?.clave);
  const hayFiltros = filtrados.length !== actuaciones.length;

  // El encargado actual abre su expediente en Gestionar; el resto, en Consulta.
  const irAlExpediente = (a: Actuacion) =>
    ir({ expediente_radicado: a.expediente_radicado, etapa: pestanaDeActuacion(a), gestionar: !!a.acto?.soy_encargado_actual });

  const abrir = (a: Actuacion) => a.proceso_id !== null && setAbierto({ clave: a.clave, categoria: a.categoria, procesoId: a.proceso_id });
  const precargar = (a: Actuacion) => (a.categoria === "acto" ? precargarActo : precargarInforme)(a.proceso_id);

  return (
    <>
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
            <ClipboardList className="text-success" size={20} />
          </div>
          <div>
            <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">Módulo de Infracciones</p>
            <h1 className="text-lg font-bold text-base-content">Mis actuaciones</h1>
          </div>
          {data && data.conteos.requieren_accion > 0 && (
            <span className="badge badge-info text-white ml-auto">{data.conteos.requieren_accion} requieren tu acción</span>
          )}
        </div>
      </div>

      <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-6xl mx-auto space-y-4">
          <MisActuacionesFiltros
            filtros={filtros}
            onChange={setFiltros}
            tipos={data?.filtros.tipos_documento ?? []}
            roles={data?.filtros.roles ?? []}
            opcionesEstado={estados}
            onActualizar={() => refetch()}
            actualizando={isFetching}
          />

          <div className="card bg-base-100 shadow border border-base-300">
            <div className="card-body p-0">
              {isPending ? (
                <div className="flex justify-center items-center py-16">
                  <span className="loading loading-spinner loading-lg text-success" />
                </div>
              ) : isError ? (
                <p role="alert" className="text-error text-center py-16">Error al cargar tus actuaciones</p>
              ) : filtrados.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <ClipboardList className="w-12 h-12 text-base-content/20 mb-3" />
                  <p className="text-base-content/60">
                    {hayFiltros ? "Sin resultados con los filtros aplicados" : "No tienes actuaciones por ahora"}
                  </p>
                </div>
              ) : (
                <MisActuacionesTabla
                  actuaciones={filtrados}
                  onExpediente={puedeIr ? irAlExpediente : undefined}
                  onProceso={abrir}
                  onPrecargarProceso={precargar}
                  onMatriz={(a) => a.informe && setMatrizInformeId(a.informe.id)}
                />
              )}
            </div>
          </div>
        </div>
      </div>

      <ProcesoInformeModal
        procesoId={abierto?.categoria === "informe" ? abierto.procesoId : null}
        onClose={() => setAbierto(null)}
        extraAcciones={
          filaAbierta ? (
            <>
              {puedeIr && (
                <button
                  type="button"
                  className="btn btn-sm btn-ghost gap-2 mr-auto"
                  onClick={() => {
                    setAbierto(null);
                    irAlExpediente(filaAbierta);
                  }}
                >
                  Ver en el expediente
                  <ArrowRight size={14} />
                </button>
              )}
              {filaAbierta.informe?.puede_editar_matriz && (
                <button
                  type="button"
                  className="btn btn-sm btn-outline btn-success gap-2"
                  onClick={() => setMatrizInformeId(filaAbierta.informe!.id)}
                >
                  <Leaf size={16} />
                  Editar matriz
                </button>
              )}
            </>
          ) : undefined
        }
      />

      <ProcesoActoModal
        procesoId={abierto?.categoria === "acto" ? abierto.procesoId : null}
        onClose={() => setAbierto(null)}
        onIrAlExpediente={puedeIr && filaAbierta ? () => irAlExpediente(filaAbierta) : undefined}
      />

      {matrizInformeId !== null && (
        <MatrizRecursosAfectadosModal
          isOpen
          onClose={() => setMatrizInformeId(null)}
          informeId={matrizInformeId}
          setToast={setToast}
        />
      )}
    </>
  );
}
