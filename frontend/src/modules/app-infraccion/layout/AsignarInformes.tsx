import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText } from "lucide-react";
import { ApiError } from "@shared/lib/api";
import { usePrecargarProceso } from "@features/proceso-revision";
import { informeAdapter } from "../api/informeAdapter";
import { useAsignarInformeMutation } from "../api/informes";
import ProcesoInformeModal from "../informe-tecnico/ProcesoInformeModal";
import AsignarProfesionalModal from "../modal/AsignarProfesionalModal";
import type { InformeTecnico } from "../types";
import InformesFiltros from "./asignar-informes/InformesFiltros";
import InformesTable from "./asignar-informes/InformesTable";
import { useInformesTecnicos } from "./asignar-informes/useInformesTecnicos";

type Props = {
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
};

type AsignarState = { informe: InformeTecnico; reasignar: boolean } | null;

export default function AsignarInformes({ setToast }: Props) {
  const precargar = usePrecargarProceso(informeAdapter);
  const navigate = useNavigate();
  const state = useInformesTecnicos();
  const { loading, totalCount, page, totalPages, profesionales, revisores } = state;
  const asignar = useAsignarInformeMutation();

  const [asignando, setAsignando] = useState<AsignarState>(null);
  const [procesoId, setProcesoId] = useState<number | null>(null);

  /**
   * POST asigna; PUT reasigna. Si el POST responde 409 (ya hay un proceso
   * vigente sin terminar) el modal pasa a modo reasignación y lo explica.
   */
  const handleAsignarSubmit = async (profesionalId: number, revisorId: number, fechaProgramacion: string) => {
    if (!asignando) return;
    const { informe, reasignar } = asignando;
    try {
      await asignar.mutateAsync({
        informeId: informe.id,
        reasignar,
        datos: {
          profesional_id: profesionalId,
          revisor_id: revisorId,
          ...(fechaProgramacion ? { fecha_programacion_visita: fechaProgramacion } : {}),
        },
      });
    } catch (e) {
      if (e instanceof ApiError && e.status === 409 && !reasignar) {
        setAsignando({ informe, reasignar: true });
        throw new Error(
          "El informe ya tiene un proceso de revisión en curso. Pulsa «Reasignar» para cerrarlo y crear uno nuevo.",
        );
      }
      throw new Error(e instanceof ApiError ? e.message : "Error al asignar profesional");
    }
    setToast({
      id: Date.now(),
      message: reasignar ? "Profesional reasignado exitosamente" : "Profesional asignado exitosamente",
      type: "success",
    });
  };

  const goToExpediente = (informe: InformeTecnico) =>
    navigate("/infraction/consult", {
      state: { radicadoToSelect: informe.expediente_radicado, timestamp: Date.now() },
    });

  return (
    <>
      <div className="bg-gradient-to-r from-base-100 to-base-200/50 border-b border-base-300 shadow-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
                <FileText className="text-success" size={20} />
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">
                  Módulo de Infracciones
                </p>
                <h1 className="text-lg font-bold text-base-content">Informes Técnicos</h1>
              </div>
            </div>
            {!loading && (
              <div className="text-right hidden sm:block">
                <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">Total informes</p>
                <p className="text-lg font-bold text-success leading-tight">
                  {totalCount}
                  <span className="text-xs font-normal text-base-content/60 ml-1">
                    pág. {page}/{totalPages}
                  </span>
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="w-full min-h-[calc(100vh-4rem)] bg-gradient-to-br from-base-200 to-base-300 p-4">
        <div className="max-w-7xl mx-auto space-y-4">
          <InformesFiltros state={state} />
          {state.isError && (
            <div role="alert" className="alert alert-error py-2 text-sm">
              Error al cargar informes
            </div>
          )}
          <InformesTable
            state={state}
            onGoToExpediente={goToExpediente}
            onVerProceso={(inf) => setProcesoId(inf.proceso_id)}
            onPrecargarProceso={(inf) => precargar(inf.proceso_id)}
            onAsignar={(inf) => {
              if (inf.modo === "MANUAL") {
                setToast({
                  id: Date.now(),
                  message: "Este informe está en modo de cargue manual, la asignación no está disponible.",
                  type: "error",
                });
                return;
              }
              setAsignando({ informe: inf, reasignar: inf.proceso_activo || inf.profesional_asignado_id !== null });
            }}
          />
        </div>
      </div>

      <AsignarProfesionalModal
        isOpen={asignando !== null}
        onClose={() => setAsignando(null)}
        onSubmit={handleAsignarSubmit}
        profesionales={profesionales}
        revisores={revisores}
        profesionalActualId={asignando?.informe.profesional_asignado_id}
        revisorActualId={asignando?.informe.revisor_asignado_id}
        fechaProgramacionActual={asignando?.informe.fecha_programacion_visita}
        isReassign={asignando?.reasignar ?? false}
      />

      {/* El líder ve el proceso; las acciones las decide el backend por usuario. */}
      <ProcesoInformeModal procesoId={procesoId} onClose={() => setProcesoId(null)} />
    </>
  );
}
