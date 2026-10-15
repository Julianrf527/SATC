import { useState } from "react";
import { AlertCircle, FileSignature } from "lucide-react";
import { toastService } from "@shared/lib/toastService";
import { useConceptoTecnicoQuery, useVersionFinalConceptoMutation } from "../../api/etapas";
import { mensajeEscritura, mensajeError } from "../../api/errors";
import { useInvalidarExpediente } from "../../api/invalidar";
import type { ConceptoParaTecnico } from "../../types";
import { CampoPdf } from "../../etapas/comun/campos/Campos";
import CamposConcepto from "../../etapas/comun/campos/CamposConcepto";
import {
  bodyConceptoFinal,
  conceptoFinalInicial,
  validarConceptoFinal,
  type ConceptoFinalForm,
} from "../../etapas/formularios/conceptoFinal";

type Props = {
  /** `etapa_ref_id` de la fila de Mis informes = id del concepto (C.4). */
  conceptoId: number;
  onCargado: () => void;
};

/**
 * El técnico no entra a Gestionar: con su concepto "Aprobado para firma"
 * carga aquí la versión firmada y los datos que pide el backend (`campos`
 * de GET /etapas/conceptos/{id}).
 */
export default function CargarConceptoFinal({ conceptoId, onCargado }: Props) {
  const query = useConceptoTecnicoQuery(conceptoId);

  if (query.isPending) {
    return (
      <div className="flex justify-center py-4">
        <span className="loading loading-spinner loading-md text-success" />
      </div>
    );
  }
  if (query.isError || !query.data) {
    return (
      <div role="alert" className="alert alert-error py-2 text-sm">
        <AlertCircle size={16} />
        <span>{mensajeError(query.error, "No se pudo cargar el concepto")}</span>
      </div>
    );
  }
  if (!query.data.acciones_disponibles.includes("cargar_version_final")) return null;
  return <Formulario key={query.data.id} concepto={query.data} onCargado={onCargado} />;
}

function Formulario({ concepto, onCargado }: { concepto: ConceptoParaTecnico; onCargado: () => void }) {
  const [form, setForm] = useState<ConceptoFinalForm>(() => conceptoFinalInicial(concepto.datos));
  const [error, setError] = useState<string | null>(null);
  const cargar = useVersionFinalConceptoMutation(concepto.id);
  const invalidarExpediente = useInvalidarExpediente(concepto.expediente.id);

  const guardar = () => {
    const invalido = validarConceptoFinal(form, concepto.campos);
    if (invalido) return setError(invalido);
    setError(null);
    cargar.mutate(
      { archivo: form.archivo as File, body: (fileId) => bodyConceptoFinal(form, concepto.campos, fileId) },
      {
        onSuccess: (res) => {
          void invalidarExpediente();
          toastService.showToast({ id: Date.now(), message: res?.message || "Concepto técnico cargado", type: "success" });
          onCargado();
        },
        onError: (err) => setError(mensajeEscritura(err, "Error al cargar el concepto")),
      },
    );
  };

  return (
    <div className="border border-success/40 bg-success/5 rounded-lg p-4 space-y-4">
      <div className="flex items-center gap-2">
        <FileSignature size={18} className="text-success" />
        <div>
          <p className="font-semibold text-sm">Cargar versión final del concepto</p>
          <p className="text-xs text-base-content/60">
            {concepto.etiqueta} · {concepto.expediente.expediente} · {concepto.expediente.nombre_predio}
          </p>
        </div>
      </div>
      <fieldset disabled={cargar.isPending} className="space-y-4">
        <CampoPdf
          etiqueta="Concepto firmado (PDF)"
          archivo={form.archivo}
          onChange={(archivo) => setForm((f) => ({ ...f, archivo }))}
          requerido
        />
        <CamposConcepto form={form} onChange={(c) => setForm((f) => ({ ...f, ...c }))} campos={concepto.campos} />
      </fieldset>
      {error && (
        <div role="alert" className="alert alert-error py-2 text-sm">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}
      <div className="flex justify-end">
        <button type="button" className="btn btn-success btn-sm text-white gap-1.5" onClick={guardar} disabled={cargar.isPending}>
          {cargar.isPending ? <span className="loading loading-spinner loading-xs" /> : <FileSignature size={14} />}
          Cargar versión final
        </button>
      </div>
    </div>
  );
}
