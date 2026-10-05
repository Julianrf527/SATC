import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FileText, Leaf } from "lucide-react";
import { usePrecargarProceso } from "@features/proceso-revision";
import { informeAdapter } from "../api/informeAdapter";
import { useMisInformesQuery } from "../api/informes";
import { opcionesEstado } from "../informe-tecnico/estadoInforme";
import ProcesoInformeModal from "../informe-tecnico/ProcesoInformeModal";
import MatrizRecursosAfectadosModal from "../modal/MatrizRecursosAfectadosModal";
import type { MiInforme } from "../types";
import { FILTROS_MIS_INFORMES, filtrarMisInformes } from "./mis-informes/filtros";
import MisInformesFiltros from "./mis-informes/MisInformesFiltros";
import MisInformesTabla from "./mis-informes/MisInformesTabla";

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

/** Id del informe que manda una notificación `informe_tecnico` (`informeIdToSelect`). */
function informeDesdeNotificacion(state: unknown): number | null {
  const id = Number((state as { informeIdToSelect?: string } | null)?.informeIdToSelect);
  return Number.isInteger(id) && id > 0 ? id : null;
}

export default function MisInformes({ setToast }: Props) {
  const precargar = usePrecargarProceso(informeAdapter);
  const navigate = useNavigate();
  const location = useLocation();
  const { data: informes = [], isPending, isFetching, isError, refetch } = useMisInformesQuery();

  const [filtros, setFiltros] = useState(FILTROS_MIS_INFORMES);
  const [informeAbierto, setInformeAbierto] = useState<number | null>(null);
  const [matrizInformeId, setMatrizInformeId] = useState<number | null>(null);
  const [pendienteNotificacion, setPendienteNotificacion] = useState<number | null>(null);

  // Notificación: se guarda el informe y se abre cuando llegue la lista.
  useEffect(() => {
    const id = informeDesdeNotificacion(location.state);
    if (id !== null) {
      setPendienteNotificacion(id);
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  useEffect(() => {
    if (pendienteNotificacion === null || isPending) return;
    const informe = informes.find((i) => i.id === pendienteNotificacion);
    if (informe?.proceso_id != null) {
      setInformeAbierto(informe.id);
    } else {
      setToast({
        id: Date.now(),
        message: informe ? "Este informe no tiene un proceso de revisión vigente" : "El informe ya no está asignado a ti",
        type: "error",
      });
    }
    setPendienteNotificacion(null);
  }, [pendienteNotificacion, isPending, informes, setToast]);

  const filtrados = useMemo(() => filtrarMisInformes(informes, filtros), [informes, filtros]);
  const estados = useMemo(() => opcionesEstado(informes), [informes]);
  // Fila fresca (se re-lee tras invalidar): decide el botón de la matriz.
  const abierto: MiInforme | undefined = informes.find((i) => i.id === informeAbierto);
  const hayFiltros = filtrados.length !== informes.length;

  const irAlExpediente = (informe: MiInforme) =>
    navigate("/infraction/consult", {
      state: { radicadoToSelect: informe.expediente_radicado, timestamp: Date.now() },
    });

  return (
    <>
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
            <FileText className="text-success" size={20} />
          </div>
          <div>
            <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">Módulo de Infracciones</p>
            <h1 className="text-lg font-bold text-base-content">Mis Informes</h1>
          </div>
        </div>
      </div>

      <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-6xl mx-auto space-y-4">
          <MisInformesFiltros
            filtros={filtros}
            onChange={setFiltros}
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
                <p role="alert" className="text-error text-center py-16">Error al cargar tus informes</p>
              ) : filtrados.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <FileText className="w-12 h-12 text-base-content/20 mb-3" />
                  <p className="text-base-content/60">
                    {hayFiltros ? "Sin resultados con los filtros aplicados" : "No tienes informes técnicos asignados"}
                  </p>
                </div>
              ) : (
                <MisInformesTabla
                  informes={filtrados}
                  onExpediente={irAlExpediente}
                  onProceso={(inf) => setInformeAbierto(inf.id)}
                  onPrecargarProceso={(inf) => precargar(inf.proceso_id)}
                  onMatriz={(inf) => setMatrizInformeId(inf.id)}
                />
              )}
            </div>
          </div>
        </div>
      </div>

      <ProcesoInformeModal
        procesoId={abierto?.proceso_id ?? null}
        onClose={() => setInformeAbierto(null)}
        extraAcciones={
          abierto?.puede_diligenciar_matriz ? (
            <button type="button" className="btn btn-sm btn-outline btn-success gap-2" onClick={() => setMatrizInformeId(abierto.id)}>
              <Leaf size={16} />
              {abierto.tiene_matriz ? "Editar matriz" : "Diligenciar matriz"}
            </button>
          ) : undefined
        }
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
