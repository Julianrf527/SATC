import type React from "react";
import { useState } from "react";
import type { Involucrado } from "@shared/types/involucrado";
import { getErrorMessage } from "@shared/lib/api";
import ConfirmDeleteModal from "./ConfirmDeleteModal";
import InvolucradoFormView from "./InvolucradoFormView";
import InvolucradoItem from "./InvolucradoItem";
import { useInvolucradoForm } from "./useInvolucradoForm";
import {
  useDesvincularInvolucradoMutation,
  useInvolucradosExpedienteQuery,
  useVincularInvolucradoMutation,
} from "./api/involucrados";
import type { InvolucradosExpedienteEndpoints, SetToast } from "./types";

interface Props {
  expedienteId: number;
  involucradosList: Involucrado[];
  endpoints: InvolucradosExpedienteEndpoints;
  onInvolucradosUpdate?: (updatedInvolucrados: Involucrado[]) => void;
  setToast: SetToast;
  isEditable?: boolean;
}

export default function InvolucradoExpediente({
  expedienteId, involucradosList, endpoints, onInvolucradosUpdate, setToast, isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(false);
  const [involucradoAEliminar, setInvolucradoAEliminar] = useState<Involucrado | null>(null);
  const form = useInvolucradoForm(setToast);

  const listarUrl = endpoints.listar(expedienteId);
  const listQuery = useInvolucradosExpedienteQuery(listarUrl);
  const vincular = useVincularInvolucradoMutation(endpoints.vincular, expedienteId, listarUrl);
  const desvincular = useDesvincularInvolucradoMutation(endpoints.desvincular, listarUrl);

  // Lo del servicio manda; si aún no llega (o falla) se muestra lo de props.
  const involucrados = listQuery.data ?? involucradosList ?? [];
  const isLoading = form.isSearching || vincular.isPending || desvincular.isPending;

  const resetForm = () => { form.reset(); setShowForm(false); };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    vincular.mutate(
      { formData: form.formData, existingInvolucrado: form.existingInvolucrado, actuales: involucrados },
      {
        onSuccess: (invData) => {
          onInvolucradosUpdate?.([...involucrados, invData]);
          resetForm();
          setToast({ id: Date.now(), message: "Involucrado vinculado exitosamente", type: "success" });
        },
        onError: (error) => {
          setToast({ id: Date.now(), message: getErrorMessage(error), type: "error" });
        },
      },
    );
  };

  const eliminarInvolucrado = (inv: Involucrado) => {
    desvincular.mutate(inv.id, {
      onSuccess: () => {
        onInvolucradosUpdate?.(involucrados.filter((i) => i.id !== inv.id));
        setToast({ id: Date.now(), message: "Involucrado desvinculado exitosamente", type: "success" });
      },
      onError: (error) => {
        setToast({ id: Date.now(), message: getErrorMessage(error), type: "error" });
      },
    });
  };

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-0">

        {involucradoAEliminar && (
          <ConfirmDeleteModal
            involucrado={involucradoAEliminar}
            isOpen
            onClose={() => setInvolucradoAEliminar(null)}
            onConfirm={() => {
              const inv = involucradoAEliminar;
              setInvolucradoAEliminar(null);
              eliminarInvolucrado(inv);
            }}
          />
        )}

        {/* Header */}
        <div className="px-5 py-4 border-b border-base-200 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-warning/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-warning" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">Expediente</p>
              <h2 className="text-base font-bold text-base-content">Presuntos Infractores</h2>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {involucrados.length > 0 && (
              <div className="flex flex-col items-center px-2.5 py-1 bg-base-200 rounded-lg min-w-[3rem]">
                <span className="text-lg font-bold leading-tight text-tono-warning">{involucrados.length}</span>
                <span className="text-[9px] text-base-content/60 uppercase">
                  {involucrados.length === 1 ? "Persona" : "Personas"}
                </span>
              </div>
            )}
            {!showForm && isEditable && (
              <button
                className="btn btn-warning btn-sm text-white gap-1.5"
                onClick={() => setShowForm(true)}
                disabled={isLoading}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Agregar
              </button>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="p-4">
          {/* Lista */}
          {!showForm && (
            <>
              {involucrados.length === 0 ? (
                <div className="text-center py-8">
                  <div className="w-12 h-12 bg-base-200 rounded-full flex items-center justify-center mb-3 mx-auto">
                    <svg className="w-6 h-6 text-base-content/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </div>
                  <p className="text-sm font-medium text-base-content/70">Sin involucrados</p>
                  <p className="text-xs text-base-content/60">No hay personas vinculadas a este expediente</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {involucrados.map((inv, idx) => (
                    <InvolucradoItem
                      key={`${inv.tipo_documento}-${inv.numero_documento}-${idx}`}
                      inv={inv}
                      isLoading={isLoading}
                      onDelete={isEditable ? () => setInvolucradoAEliminar(inv) : undefined}
                    />
                  ))}
                </div>
              )}
            </>
          )}

          {/* Formulario */}
          {showForm && isEditable && (
            <InvolucradoFormView
              form={form}
              isLoading={isLoading}
              onSubmit={handleSubmit}
              onCancel={resetForm}
            />
          )}
        </div>
      </div>
    </div>
  );
}
