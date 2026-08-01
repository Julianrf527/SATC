import { useState } from "react";
import type {
  ExpedienteDetalle,
  Quejoso,
  TipoAfectacion,
} from "../../../../types/infraccionApp";
import type { Municipio, ModeloGenerico } from "../../../../types/common";
import QuejosoSelectorModal from "../../../app-infraccion/Common/QuejosoSelectorModal";
import InformacionInfraccionView from "./InformacionInfraccionView";
import InformacionInfraccionForm from "./InformacionInfraccionForm";
import { useInformacionInfraccionForm } from "./useInformacionInfraccionForm";

interface Props {
  expediente: ExpedienteDetalle;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  tipoAfectacionList: TipoAfectacion[];
  quejosoList: Quejoso[];
  setQuejosoList?: (quejosos: Quejoso[]) => void;
  onUpdate?: (expediente: ExpedienteDetalle) => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
}

export default function InformacionInfraccionData({
  expediente,
  municipioList,
  recursoAfectadoList,
  tipoAfectacionList,
  quejosoList,
  setQuejosoList,
  onUpdate,
  setToast,
  isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(false);
  const [showQuejosoModal, setShowQuejosoModal] = useState(false);

  const form = useInformacionInfraccionForm({
    expediente,
    municipioList,
    recursoAfectadoList,
    tipoAfectacionList,
    quejosoList,
    setQuejosoList,
    onUpdate,
    setToast,
    onSaved: () => setShowForm(false),
    onCancelled: () => setShowForm(false),
  });

  return (
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-0">

        {/* Header */}
        <div className="px-5 py-4 border-b border-base-200 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-success/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">Expediente</p>
              <h2 className="text-base font-bold text-base-content">Datos del Expediente</h2>
            </div>
          </div>
          {!showForm && isEditable && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-success hover:bg-success/10"
              onClick={() => setShowForm(true)}
              disabled={form.isLoading}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Editar
            </button>
          )}
        </div>

        <div className="p-5">
          {!showForm && (
            <InformacionInfraccionView
              expediente={expediente}
              recursoAfectadoList={recursoAfectadoList}
            />
          )}

          {showForm && isEditable && (
            <InformacionInfraccionForm
              form={form}
              municipioList={municipioList}
              recursoAfectadoList={recursoAfectadoList}
              tipoAfectacionList={tipoAfectacionList}
              quejosoList={quejosoList}
              onOpenQuejosoModal={() => setShowQuejosoModal(true)}
            />
          )}
        </div>
      </div>

      <QuejosoSelectorModal
        isOpen={showQuejosoModal}
        title="Quejosos"
        quejosoList={quejosoList}
        selectedIds={form.quejososIds}
        onSelectionChange={form.setQuejososIds}
        onCreateQuejoso={form.handleCreateQuejoso}
        setToast={setToast}
        onClose={() => setShowQuejosoModal(false)}
        isDisabled={form.isLoading}
      />
    </div>
  );
}
