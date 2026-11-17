import { useState } from "react";
import { ApiError } from "@shared/lib/api";
import { useArchivarExpedienteMutation } from "../api/etapas";
import type { Ejecucion, EtapaEjecucion, SetToast } from "../types";
import EtapaContenedor from "./comun/EtapaContenedor";
import Icono from "./comun/Icono";
import { useEtapaSancionatoria } from "./comun/useEtapaSancionatoria";
import { ICONOS } from "./comun/iconos";
import EjecucionSancionData from "./ejecucion-sancion/EjecucionSancionData";
import ConfirmArchiveModal from "./ejecucion-sancion/ConfirmArchiveModal";

type Props = {
  radicado: string;
  expedienteId: number;
  onStageUpdate: (stage: string) => void;
  setToast: SetToast;
  isEditable?: boolean;
  onArchiveSuccess?: () => void;
};

const STAGE_NAME = "EJECUCION DE LA SANCION";

export default function EjecucionSancion({
  radicado,
  expedienteId,
  onStageUpdate,
  setToast,
  isEditable = true,
  onArchiveSuccess,
}: Props) {
  const etapa = useEtapaSancionatoria<EtapaEjecucion>({
    etapa: "ejecucion",
    expedienteId,
    nombreEtapa: STAGE_NAME,
    mensajeErrorCarga: "Error al cargar ejecución de la sanción.",
    setToast,
    onStageUpdate,
    alRechazarCreacion: "bloquear",
  });
  const archivar = useArchivarExpedienteMutation(expedienteId);
  const [showArchiveModal, setShowArchiveModal] = useState(false);

  // Hay datos registrados cuando la ejecución trae el acto (tipo_acto). Recién
  // creada con "Crear Etapa" la etapa existe pero aún sin datos.
  const executionData =
    etapa.datos?.etapa_id && etapa.datos.tipo_acto ? (etapa.datos as Ejecucion) : undefined;

  const handleArchiveConfirm = () => {
    if (!expedienteId) return;
    archivar.mutate(undefined, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Expediente archivado exitosamente.", type: "success" });
        setShowArchiveModal(false);
        onStageUpdate(STAGE_NAME);
        onArchiveSuccess?.();
      },
      onError: (e) =>
        setToast({
          id: Date.now(),
          message: e instanceof ApiError ? e.message : "Error al archivar el expediente.",
          type: "error",
        }),
    });
  };

  return (
    <EtapaContenedor
      expedienteId={expedienteId}
      nombreEtapa={STAGE_NAME}
      textoCarga="Obteniendo información de ejecución de la sanción"
      textoCrear="Para continuar, debe crear esta etapa y así poder gestionar la información de ejecución de la sanción."
      icono={ICONOS.portapapeles}
      isEditable={isEditable}
      cargando={etapa.cargando}
      mostrarCarga={etapa.mostrarCarga}
      etapaExiste={etapa.etapaExiste}
      creable={etapa.creable}
      creando={etapa.creando}
      onCrear={etapa.crearEtapa}
    >
      <div className="space-y-6">
        <EjecucionSancionData
          data={executionData}
          setToast={setToast}
          expedienteId={expedienteId}
          onDataUpdated={() => void etapa.refrescar()}
          isEditable={isEditable}
        />

        {/* Archivar - solo con datos guardados y en modo edición */}
        {executionData && isEditable && (
          <div className="card bg-gradient-to-br from-warning/5 to-warning/10 shadow-lg border border-warning/20">
            <div className="card-body">
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-warning/20 rounded-full flex items-center justify-center flex-shrink-0">
                    <Icono d={ICONOS.archivar} className="w-6 h-6 text-warning" />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg mb-1">Archivar Expediente</h3>
                    <p className="text-sm text-base-content/70">
                      Una vez completada la ejecución de la sanción, puede
                      archivar este expediente. Los expedientes archivados no
                      aparecerán en la gestión pero seguirán disponibles para
                      consulta.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowArchiveModal(true)}
                  className="btn btn-warning text-white gap-2 shadow-md hover:shadow-lg transition-all whitespace-nowrap"
                >
                  <Icono d={ICONOS.archivar} className="w-5 h-5" />
                  Archivar Expediente
                </button>
              </div>
            </div>
          </div>
        )}

        <ConfirmArchiveModal
          isOpen={showArchiveModal}
          onClose={() => setShowArchiveModal(false)}
          onConfirm={handleArchiveConfirm}
          radicado={radicado}
          isArchiving={archivar.isPending}
        />
      </div>
    </EtapaContenedor>
  );
}
