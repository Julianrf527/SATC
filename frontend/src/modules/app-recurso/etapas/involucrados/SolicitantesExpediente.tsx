import { useState } from "react";
import { UserMinus, Users } from "lucide-react";
import { Modal } from "@shared/ui";
import { useDesvincularMutation } from "../../api/involucrados";
import { mensajeError } from "../../api/errors";
import type { ExpedienteDetalle, SetToast, VinculoInvolucrado } from "../../types";
import { nombrePersona } from "./personaForm";
import RepresentanteModal from "./RepresentanteModal";
import SolicitanteItem from "./SolicitanteItem";
import VincularSolicitanteForm from "./VincularSolicitanteForm";

type Props = {
  expediente: ExpedienteDetalle;
  setToast: SetToast;
  isEditable: boolean;
};

/**
 * Solicitantes del expediente (plan §3). Réplica de
 * `@features/involucrados-expediente`: aquella no maneja representante legal
 * (V14), `version` al desvincular ni la forma de vínculo de app-recurso, y su
 * título es "Presuntos Infractores". Los botones salen de
 * `acciones_disponibles` (expediente y vínculo).
 */
export default function SolicitantesExpediente({ expediente, setToast, isEditable }: Props) {
  const [vinculando, setVinculando] = useState(false);
  const [editarRep, setEditarRep] = useState<VinculoInvolucrado | null>(null);
  const [desvincularDe, setDesvincularDe] = useState<VinculoInvolucrado | null>(null);
  const desvincular = useDesvincularMutation(expediente.id);

  const solicitantes = expediente.involucrados.filter((v) => v.tipo_vinculo === "SOLICITANTE");
  const puedeVincular = isEditable && expediente.acciones_disponibles.includes("vincular_solicitante");
  const accion = (v: VinculoInvolucrado, codigo: string) => isEditable && (v.acciones_disponibles ?? []).includes(codigo);

  const confirmarDesvincular = () => {
    if (!desvincularDe) return;
    desvincular.mutate(desvincularDe, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Solicitante desvinculado", type: "success" });
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
              <Users size={16} className="text-warning" />
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">Expediente</p>
              <h2 className="text-base font-bold text-base-content">Solicitantes</h2>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {solicitantes.length > 0 && (
              <div className="flex flex-col items-center px-2.5 py-1 bg-base-200 rounded-lg min-w-[3rem]">
                <span className="text-lg font-bold leading-tight text-tono-warning">{solicitantes.length}</span>
                <span className="text-[9px] text-base-content/60 uppercase">{solicitantes.length === 1 ? "Persona" : "Personas"}</span>
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
            <VincularSolicitanteForm expedienteId={expediente.id} setToast={setToast} onCerrar={() => setVinculando(false)} />
          ) : solicitantes.length === 0 ? (
            <div className="text-center py-8">
              <div className="w-12 h-12 bg-base-200 rounded-full flex items-center justify-center mb-3 mx-auto">
                <Users size={20} className="text-base-content/40" />
              </div>
              <p className="text-sm font-medium text-base-content/70">Sin solicitantes</p>
              <p className="text-xs text-base-content/60">No hay personas vinculadas a este expediente</p>
            </div>
          ) : (
            <div className="space-y-2">
              {solicitantes.map((v) => (
                <SolicitanteItem
                  key={v.id}
                  vinculo={v}
                  ocupado={desvincular.isPending}
                  onEditarRepresentante={accion(v, "editar_representante") ? () => setEditarRep(v) : undefined}
                  onDesvincular={accion(v, "desvincular") ? () => setDesvincularDe(v) : undefined}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {editarRep && (
        <RepresentanteModal
          expedienteId={expediente.id}
          vinculo={editarRep}
          setToast={setToast}
          onClose={() => setEditarRep(null)}
        />
      )}

      <Modal
        isOpen={desvincularDe !== null}
        onClose={() => setDesvincularDe(null)}
        size="sm"
        icon={<UserMinus size={20} />}
        title="Desvincular solicitante"
        closeOnEsc={!desvincular.isPending}
        footer={
          <>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setDesvincularDe(null)} disabled={desvincular.isPending}>
              Cancelar
            </button>
            <button type="button" className="btn btn-error btn-sm text-white" onClick={confirmarDesvincular} disabled={desvincular.isPending}>
              {desvincular.isPending && <span className="loading loading-spinner loading-xs" />}
              Desvincular
            </button>
          </>
        }
      >
        <p className="text-sm">
          ¿Desvincular a <span className="font-semibold">{nombrePersona(desvincularDe?.involucrado)}</span> de este expediente? La
          persona no se borra del registro de involucrados.
        </p>
      </Modal>
    </div>
  );
}
