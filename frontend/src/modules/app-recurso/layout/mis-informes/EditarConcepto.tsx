import { useState } from "react";
import { AlertCircle, Pencil, Save } from "lucide-react";
import { toastService } from "@shared/lib/toastService";
import { useConceptoTecnicoQuery, useEditarConceptoMutation } from "../../api/etapas";
import { mensajeEscritura } from "../../api/errors";
import type { ConceptoParaTecnico } from "../../types";
import { CampoPdf } from "../../etapas/comun/campos/Campos";
import CamposConcepto from "../../etapas/comun/campos/CamposConcepto";
import {
  bodyConceptoFinal,
  conceptoFinalInicial,
  validarCamposConcepto,
  type ConceptoFinalForm,
} from "../../etapas/formularios/conceptoFinal";
import { esPdf } from "../../etapas/formularios/comunes";

/**
 * El técnico corrige su concepto de la etapa 2 ya cargado (datos, acción y,
 * si quiere, un nuevo PDF firmado). Solo aparece si el backend trae
 * `editar_concepto` (mientras no exista la decisión). El técnico encargado y
 * la fecha de visita no se editan aquí (vienen del auto que admite).
 */
export default function EditarConcepto({ conceptoId }: { conceptoId: number }) {
  const query = useConceptoTecnicoQuery(conceptoId);
  const [abierto, setAbierto] = useState(false);
  if (!query.data?.acciones_disponibles.includes("editar_concepto")) return null;
  if (!abierto) {
    return (
      <div className="flex justify-end">
        <button type="button" className="btn btn-outline btn-sm gap-1.5" onClick={() => setAbierto(true)}>
          <Pencil size={14} /> Editar concepto
        </button>
      </div>
    );
  }
  return (
    <Formulario
      key={`${query.data.id}-${query.data.version}`}
      concepto={query.data}
      onCerrar={() => setAbierto(false)}
    />
  );
}

function Formulario({ concepto, onCerrar }: { concepto: ConceptoParaTecnico; onCerrar: () => void }) {
  const [form, setForm] = useState<ConceptoFinalForm>(() => conceptoFinalInicial(concepto.datos));
  const [error, setError] = useState<string | null>(null);
  const editar = useEditarConceptoMutation(concepto.id, concepto.expediente.id);

  const guardar = () => {
    if (form.archivo && !esPdf(form.archivo)) return setError("El concepto firmado debe ser PDF");
    const invalido = validarCamposConcepto(form, concepto.campos);
    if (invalido) return setError(invalido);
    setError(null);
    editar.mutate(
      {
        archivo: form.archivo,
        body: (fileId) => {
          const { file_id: _sinArchivo, ...datos } = bodyConceptoFinal(form, concepto.campos, 0);
          void _sinArchivo;
          return { ...datos, version: concepto.version, ...(fileId ? { file_id: fileId } : {}) };
        },
      },
      {
        onSuccess: (res) => {
          toastService.showToast({ id: Date.now(), message: res?.message || "Concepto actualizado", type: "success" });
          onCerrar();
        },
        onError: (err) => setError(mensajeEscritura(err, "Error al editar el concepto")),
      },
    );
  };

  return (
    <div className="border border-base-300 rounded-lg p-4 space-y-4">
      <div className="flex items-center gap-2">
        <Pencil size={18} className="text-base-content/70" />
        <div>
          <p className="font-semibold text-sm">Editar concepto técnico</p>
          <p className="text-xs text-base-content/60">
            Corrija los datos o reemplace el PDF firmado. Si no adjunta un PDF se conserva el actual.
          </p>
        </div>
      </div>
      <fieldset disabled={editar.isPending} className="space-y-4">
        <CampoPdf
          etiqueta="Nuevo concepto firmado (PDF)"
          archivo={form.archivo}
          onChange={(archivo) => setForm((f) => ({ ...f, archivo }))}
          actualId={concepto.datos.doc_concepto_tecnico_id}
        />
        <CamposConcepto form={form} onChange={(c) => setForm((f) => ({ ...f, ...c }))} campos={concepto.campos} />
      </fieldset>
      {error && (
        <div role="alert" className="alert alert-error py-2 text-sm">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      <div className="flex justify-end gap-2">
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCerrar} disabled={editar.isPending}>
          Cancelar
        </button>
        <button type="button" className="btn btn-success btn-sm text-white gap-1.5" onClick={guardar} disabled={editar.isPending}>
          {editar.isPending ? <span className="loading loading-spinner loading-xs" /> : <Save size={14} />}
          Guardar cambios
        </button>
      </div>
    </div>
  );
}
