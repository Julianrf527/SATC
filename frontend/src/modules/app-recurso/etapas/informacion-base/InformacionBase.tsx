import { useState } from "react";
import { Pencil } from "lucide-react";
import type { EtapaProps } from "../tipos";
import SolicitantesExpediente from "../involucrados/SolicitantesExpediente";
import TerceroInterviniente from "../tercero-interviniente/TerceroInterviniente";
import InformacionBaseForm from "./InformacionBaseForm";
import InformacionBaseView from "./InformacionBaseView";

/**
 * Pestaña "Información base": datos de nacimiento del expediente (§3),
 * solicitantes y terceros intervinientes (transversal, no es una etapa). Editar se ofrece solo si el backend manda
 * `editar_informacion_base` en `acciones_disponibles`.
 */
export default function InformacionBase({ expediente, etapas, catalogos, setToast, isEditable }: EtapaProps) {
  const [editando, setEditando] = useState(false);
  const puedeEditar = isEditable && expediente.acciones_disponibles.includes("editar_informacion_base");

  return (
    <div className="space-y-6">
      <div className="card bg-base-100 shadow border border-base-300">
        <div className="card-body p-0">
          <div className="px-5 py-4 border-b border-base-200 flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 bg-info/10 rounded-lg flex items-center justify-center flex-shrink-0">
                <i className="bx bx-info-circle text-info text-lg"></i>
              </div>
              <div>
                <p className="text-[10px] font-semibold text-base-content/60 uppercase tracking-wider">Expediente</p>
                <h2 className="text-base font-bold text-base-content">Información base</h2>
              </div>
            </div>
            {puedeEditar && !editando && (
              <button type="button" className="btn btn-sm btn-outline gap-1.5" onClick={() => setEditando(true)}>
                <Pencil size={14} />
                Editar
              </button>
            )}
          </div>
          <div className="p-5">
            {editando && puedeEditar ? (
              <InformacionBaseForm
                expediente={expediente}
                catalogos={catalogos}
                setToast={setToast}
                onCerrar={() => setEditando(false)}
              />
            ) : (
              <InformacionBaseView expediente={expediente} />
            )}
          </div>
        </div>
      </div>

      <SolicitantesExpediente expediente={expediente} setToast={setToast} isEditable={isEditable} />

      <TerceroInterviniente
        expediente={expediente}
        etapas={etapas}
        catalogos={catalogos}
        setToast={setToast}
        isEditable={isEditable}
      />
    </div>
  );
}
