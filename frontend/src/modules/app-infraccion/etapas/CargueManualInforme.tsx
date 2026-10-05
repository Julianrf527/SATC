import { useState } from "react";
import { Check } from "lucide-react";
import { useAuth } from "@shared/context/AuthContext";
import { openDocumentById } from "@shared/lib/documentViewer";
import { formatDate } from "@shared/lib/format";
import { Modal } from "@shared/ui";
import { detalleError } from "../api/errors";
import { useCambiarModoMutation } from "../api/informes";
import CargueManualForm from "../informe-tecnico/CargueManualForm";
import type { InformeTecnico, ModoInforme } from "../types";

const PERMISO_CARGUE = "infraccion_cargue";

type Props = {
  informe: InformeTecnico;
  setToast: (toast: { id: number; message: string; type: "success" | "error" }) => void;
  isEditable: boolean;
};

/**
 * Modo de cargue del informe (FLUJO ↔ MANUAL) y, en MANUAL, el cargue directo.
 * Solo para quien tiene `infraccion_cargue`. Tras cada cambio las mutaciones
 * invalidan la etapa y los listados de informes.
 */
export default function CargueManualInforme({ informe, setToast, isEditable }: Props) {
  const { user } = useAuth();
  const tieneCarguePermiso = isEditable && (user?.permisos ?? []).some((p) => p.name === PERMISO_CARGUE);
  const cambiarModo = useCambiarModoMutation(informe.id);
  const [confirmModo, setConfirmModo] = useState<ModoInforme | null>(null);
  const [editando, setEditando] = useState(false);

  if (!tieneCarguePermiso) return null;

  const esManual = informe.modo === "MANUAL";

  const confirmar = () => {
    if (!confirmModo) return;
    cambiarModo.mutate(confirmModo, {
      onSuccess: () =>
        setToast({
          id: Date.now(),
          message: confirmModo === "MANUAL" ? "Cambiado a cargue manual" : "Cambiado a flujo normal",
          type: "success",
        }),
      onError: (e) => setToast({ id: Date.now(), message: detalleError(e) ?? "Error al cambiar el modo", type: "error" }),
      onSettled: () => setConfirmModo(null),
    });
  };

  return (
    <div className="card bg-base-200/50 border border-base-300">
      <div className="card-body space-y-4 p-4">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <p className="text-sm text-base-content/70">
            Modo de cargue:{" "}
            <span className="font-semibold text-base-content">{esManual ? "Manual" : "Flujo normal"}</span>
          </p>
          <button
            type="button"
            className="btn btn-sm btn-ghost gap-2"
            onClick={() => setConfirmModo(esManual ? "FLUJO" : "MANUAL")}
            disabled={cambiarModo.isPending}
          >
            Cambiar a {esManual ? "flujo normal" : "cargue manual"}
          </button>
        </div>

        {esManual && informe.documento_informe_id && !editando && (
          <div className="flex items-center justify-between gap-3 p-3 bg-base-100 rounded-lg border border-base-300">
            <p className="text-sm text-base-content/70 flex items-center gap-2">
              <Check size={16} className="text-success shrink-0" />
              Informe cargado manualmente el {formatDate(informe.fecha_aceptacion_informe)}.
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => openDocumentById(informe.documento_informe_id!)}
                className="btn btn-ghost btn-xs gap-1 text-success"
              >
                Ver archivo
              </button>
              <button type="button" onClick={() => setEditando(true)} className="btn btn-outline btn-xs gap-1">
                Editar
              </button>
            </div>
          </div>
        )}

        {esManual && (!informe.documento_informe_id || editando) && (
          <CargueManualForm
            key={`${informe.id}-${informe.documento_informe_id ?? 0}`}
            informe={informe}
            setToast={setToast}
            editando={editando}
            onTerminar={() => setEditando(false)}
          />
        )}
      </div>

      <Modal
        isOpen={confirmModo !== null}
        onClose={() => setConfirmModo(null)}
        size="md"
        title={`Cambiar a ${confirmModo === "MANUAL" ? "cargue manual" : "flujo normal"}`}
        closeOnEsc={!cambiarModo.isPending}
        closeOnBackdrop={!cambiarModo.isPending}
        footer={
          <>
            <button className="btn btn-ghost btn-sm" onClick={() => setConfirmModo(null)} disabled={cambiarModo.isPending}>
              Cancelar
            </button>
            <button className="btn btn-warning btn-sm text-white" onClick={confirmar} disabled={cambiarModo.isPending}>
              {cambiarModo.isPending ? <span className="loading loading-spinner loading-xs" /> : "Sí, cambiar"}
            </button>
          </>
        }
      >
        <p className="text-sm text-base-content/70">
          Esto eliminará por completo la información del modo actual (archivo, fechas
          {informe.modo === "FLUJO" ? ", profesional, revisor y el proceso de revisión" : ""}). Esta acción no se
          puede deshacer. ¿Continuar?
        </p>
      </Modal>
    </div>
  );
}
