import { useCallback, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Modal } from "@shared/ui";
import { useDelayedFlag } from "@shared/hooks/useDelayedFlag";
import { useCierreEtapaQuery, useCrearCierreMutation } from "../api/etapas";
import { useArchivarExpedienteMutation } from "../api/expediente";
import { detalleError, esErrorDeConexion } from "../api/errors";
import { infraccionKeys } from "../api/queryKeys";
import CierreActo from "./cierre/CierreActo";
import {
  EtapaCargando,
  EtapaHueco,
  EtapaNoCreable,
  EtapaNoExiste,
  EtapaPorCrear,
  EtapaSinExpediente,
  IconoEtapa,
  IconoMas,
} from "./EtapaEstados";
import { ICONOS_ETAPA } from "./iconosEtapa";
import { useAvisoErrorCarga } from "./useAvisoErrorCarga";

type Props = {
  expedienteId: number;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
  onStageUpdate: (stage: string) => void;
  isEditable?: boolean;
  onArchiveSuccess?: () => void;
};

const STAGE_NAME = "Cierre";

export default function Cierre({
  expedienteId,
  setToast,
  onStageUpdate,
  isEditable = true,
  onArchiveSuccess,
}: Props) {
  const queryClient = useQueryClient();
  const query = useCierreEtapaQuery(expedienteId);
  const crearCierre = useCrearCierreMutation(expedienteId);
  const archivar = useArchivarExpedienteMutation(expedienteId);
  const showLoading = useDelayedFlag(query.isPending && !!expedienteId, 300);
  const [showArchiveModal, setShowArchiveModal] = useState(false);
  const isArchiving = archivar.isPending;

  useAvisoErrorCarga(query.error, setToast, {
    http: "Error al cargar la etapa de cierre",
    conexion: "Error de conexión al cargar el cierre",
  });

  const cierreData = query.data?.data ?? null;
  const creable = query.data?.creable ?? false;
  const creableMsg = query.data?.creableMsg ?? null;

  const mensajeError = (err: unknown, fallback: string) =>
    esErrorDeConexion(err) ? "Error de conexión" : (detalleError(err) ?? fallback);

  const handleCreateStage = () => {
    crearCierre.mutate(undefined, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Etapa de cierre creada correctamente", type: "success" });
        onStageUpdate(STAGE_NAME);
      },
      onError: (err) =>
        setToast({ id: Date.now(), message: mensajeError(err, "Error al crear la etapa"), type: "error" }),
    });
  };

  const handleArchiveConfirm = () => {
    archivar.mutate(undefined, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Expediente archivado exitosamente", type: "success" });
        setShowArchiveModal(false);
        onStageUpdate(STAGE_NAME);
        onArchiveSuccess?.();
      },
      onError: (err) =>
        setToast({ id: Date.now(), message: mensajeError(err, "Error al archivar el expediente"), type: "error" }),
    });
  };

  const handleDataUpdated = useCallback(
    () => queryClient.invalidateQueries({ queryKey: infraccionKeys.cierre(expedienteId) }),
    [queryClient, expedienteId],
  );

  const notifsCierre = cierreData?.acto_admin?.notificacion?.involucrados ?? [];
  const todasNotificadas =
    !!cierreData?.acto_admin &&
    notifsCierre.length > 0 &&
    notifsCierre.every((n) => n.notificacion_exitosa === true);

  if (showLoading) return <EtapaCargando etapa={STAGE_NAME} />;
  if (!expedienteId) return <EtapaSinExpediente isEditable={isEditable} />;
  if (query.isPending) return <EtapaHueco />;

  if (!cierreData && !isEditable) return <EtapaNoExiste etapa={STAGE_NAME} />;
  if (!cierreData && !creable) return <EtapaNoCreable motivo={creableMsg} />;

  if (!cierreData) {
    return (
      <EtapaPorCrear
        etapa={STAGE_NAME}
        icono={ICONOS_ETAPA.archivo}
        descripcion="Para continuar, cree esta etapa y registre el acto administrativo de cierre."
      >
        <button
          className="btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
          onClick={handleCreateStage}
          disabled={crearCierre.isPending}
        >
          {crearCierre.isPending ? (
            <><span className="loading loading-spinner loading-sm" />Creando etapa...</>
          ) : (
            <>
              <IconoMas />
              Crear Etapa
            </>
          )}
        </button>
      </EtapaPorCrear>
    );
  }

  return (
    <div className="space-y-6">
      {/* Acto + Notificaciones */}
      <CierreActo
        etapaCierreId={cierreData.id}
        expedienteId={expedienteId}
        actoAdmin={cierreData.acto_admin}
        isEditable={isEditable}
        setToast={setToast}
        onDataUpdated={handleDataUpdated}
      />

      {/* Archivar — solo si todos notificados exitosamente */}
      {todasNotificadas && isEditable && (
        <div className="card bg-warning/5 shadow-lg">
          <div className="card-body">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-warning/20 rounded-full flex items-center justify-center flex-shrink-0">
                  <IconoEtapa d={ICONOS_ETAPA.archivo} className="w-6 h-6 text-warning" />
                </div>
                <div>
                  <h3 className="font-bold text-lg mb-1">Archivar Expediente</h3>
                  <p className="text-sm text-base-content/70">
                    Todos los involucrados han sido notificados exitosamente. Puede archivar este expediente.
                    Los expedientes archivados seguirán disponibles para consulta.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowArchiveModal(true)}
                className="btn btn-warning text-white gap-2 shadow-md hover:shadow-lg transition-all whitespace-nowrap"
              >
                <IconoEtapa d={ICONOS_ETAPA.archivo} className="w-5 h-5" />
                Archivar Expediente
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal confirmación archivo */}
      <Modal
        isOpen={showArchiveModal}
        onClose={() => !isArchiving && setShowArchiveModal(false)}
        closeOnEsc={!isArchiving}
        title="Confirmar archivo del expediente"
        icon={<IconoEtapa d={ICONOS_ETAPA.alerta} className="w-5 h-5 text-warning" />}
        footer={
          <>
            <button className="btn btn-outline" onClick={() => setShowArchiveModal(false)} disabled={isArchiving}>
              Cancelar
            </button>
            <button className="btn btn-warning text-white gap-2" onClick={handleArchiveConfirm} disabled={isArchiving}>
              {isArchiving ? (
                <><span className="loading loading-spinner loading-sm" />Archivando...</>
              ) : (
                <>
                  <IconoEtapa d={ICONOS_ETAPA.archivo} className="w-4 h-4" />
                  Sí, archivar
                </>
              )}
            </button>
          </>
        }
      >
        <p className="text-base-content/80 mb-4">
          Esta acción archivará el expediente. El expediente dejará de aparecer en la lista activa
          pero seguirá disponible para consulta.
        </p>
        <p className="text-sm font-medium text-base-content">¿Está seguro de que desea continuar?</p>
      </Modal>
    </div>
  );
}
