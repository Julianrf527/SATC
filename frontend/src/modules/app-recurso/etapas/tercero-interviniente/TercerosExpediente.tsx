import { useState } from "react";
import { UserMinus, UserRoundPlus } from "lucide-react";
import { Modal } from "@shared/ui";
import { useDesvincularTerceroMutation } from "../../api/involucrados";
import { mensajeError } from "../../api/errors";
import type { ExpedienteDetalle, NodoTercero, SetToast, VinculoInvolucrado } from "../../types";
import { accionesNodo } from "../nodos";
import { nombrePersona } from "../involucrados/personaForm";
import RepresentanteModal from "../involucrados/RepresentanteModal";
import SolicitanteItem from "../involucrados/SolicitanteItem";
import VincularSolicitanteForm from "../involucrados/VincularSolicitanteForm";

type Props = {
  expediente: ExpedienteDetalle;
  terceros: NodoTercero[];
  /** El árbol trae `vincular_tercero` en sus acciones. */
  puedeVincular: boolean;
  setToast: SetToast;
  isEditable: boolean;
};

/**
 * Personas vinculadas como tercero interviniente (plan §4, transversal), con
 * el mismo formato que la tarjeta de Solicitantes: vincular, representante
 * legal y desvincular. El acto que reconoce a cada uno va en su propia
 * tarjeta, debajo (TerceroCard).
 */
export default function TercerosExpediente({ expediente, terceros, puedeVincular, setToast, isEditable }: Props) {
  const [vinculando, setVinculando] = useState(false);
  const [editarRep, setEditarRep] = useState<NodoTercero | null>(null);
  const [desvincularDe, setDesvincularDe] = useState<NodoTercero | null>(null);
  const quitar = useDesvincularTerceroMutation(expediente.id);

  const confirmarDesvincular = () => {
    if (!desvincularDe) return;
    quitar.mutate(desvincularDe, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Tercero interviniente desvinculado", type: "success" });
        setDesvincularDe(null);
      },
      onError: (err) => {
        setToast({ id: Date.now(), message: mensajeError(err, "Error al desvincular"), type: "error" });
        setDesvincularDe(null);
      },
    });
  };

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-0">
        <div className="px-5 py-4 border-b border-base-200 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-warning/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <i className="bx bx-user-voice text-warning text-lg"></i>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">Expediente</p>
              <h2 className="text-base font-bold text-base-content">Terceros intervinientes</h2>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {terceros.length > 0 && (
              <div className="flex flex-col items-center px-2.5 py-1 bg-base-200 rounded-lg min-w-[3rem]">
                <span className="text-lg font-bold leading-tight text-tono-warning">{terceros.length}</span>
                <span className="text-[9px] text-base-content/60 uppercase">{terceros.length === 1 ? "Persona" : "Personas"}</span>
              </div>
            )}
            {puedeVincular && !vinculando && (
              <button type="button" className="btn btn-warning btn-sm text-white gap-1.5" onClick={() => setVinculando(true)}>
                + Agregar
              </button>
            )}
          </div>
        </div>

        <div className="p-4">
          {vinculando && puedeVincular ? (
            <VincularSolicitanteForm expedienteId={expediente.id} setToast={setToast} onCerrar={() => setVinculando(false)} tercero />
          ) : terceros.length === 0 ? (
            <div className="text-center py-8">
              <div className="w-12 h-12 bg-base-200 rounded-full flex items-center justify-center mb-3 mx-auto">
                <UserRoundPlus size={20} className="text-base-content/40" />
              </div>
              <p className="text-sm font-medium text-base-content/70">Sin terceros intervinientes</p>
              <p className="text-xs text-base-content/60">
                Opcional: aparece cuando alguien se opone al permiso (auto admite, fijación del aviso o visita).
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {terceros.map((t) => {
                const puede = accionesNodo(t, isEditable);
                return (
                  <SolicitanteItem
                    key={t.id}
                    vinculo={t as VinculoInvolucrado}
                    ocupado={quitar.isPending}
                    onEditarRepresentante={puede("editar_representante") ? () => setEditarRep(t) : undefined}
                    onDesvincular={puede("desvincular") ? () => setDesvincularDe(t) : undefined}
                  />
                );
              })}
            </div>
          )}
        </div>
      </div>

      {editarRep && (
        <RepresentanteModal
          expedienteId={expediente.id}
          vinculo={editarRep as VinculoInvolucrado}
          setToast={setToast}
          onClose={() => setEditarRep(null)}
        />
      )}

      <Modal
        isOpen={desvincularDe !== null}
        onClose={() => setDesvincularDe(null)}
        size="sm"
        icon={<UserMinus size={20} />}
        title="Desvincular tercero interviniente"
        closeOnEsc={!quitar.isPending}
        footer={
          <>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setDesvincularDe(null)} disabled={quitar.isPending}>
              Cancelar
            </button>
            <button type="button" className="btn btn-error btn-sm text-white" onClick={confirmarDesvincular} disabled={quitar.isPending}>
              {quitar.isPending && <span className="loading loading-spinner loading-xs" />}
              Desvincular
            </button>
          </>
        }
      >
        <p className="text-sm">
          ¿Desvincular a <span className="font-semibold">{nombrePersona(desvincularDe?.involucrado)}</span> como tercero
          interviniente? La persona no se borra del registro de involucrados.
        </p>
      </Modal>
    </div>
  );
}
