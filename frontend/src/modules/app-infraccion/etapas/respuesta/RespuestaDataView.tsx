import { formatDate } from "@shared/lib/format";
import type { RespuestaData } from "../../types";

type Props = {
  respuestaData: RespuestaData | null;
  radicado: string;
  fechaRadicado: string;
  requiereMedida: boolean;
  isEditable: boolean;
  onViewFile: () => void;
};

const ICONO_ETIQUETA =
  "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z";
const ICONO_CALENDARIO =
  "M8 7V3m8 4V3m-9 8h10m-12 9h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v11a2 2 0 002 2z";

function Dato({ icono, etiqueta, valor }: { icono: string; etiqueta: string; valor: string }) {
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2">
        <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
          <svg className="w-4 h-4 text-base-content/70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={icono} />
          </svg>
        </div>
        <div>
          <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">{etiqueta}</p>
          <p className="text-sm font-semibold">{valor}</p>
        </div>
      </div>
    </div>
  );
}

/** Vista (no edición) de la etapa de respuesta. */
export default function RespuestaDataView({
  respuestaData,
  radicado,
  fechaRadicado,
  requiereMedida,
  isEditable,
  onViewFile,
}: Props) {
  if (respuestaData) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Dato icono={ICONO_ETIQUETA} etiqueta="Radicado SIAF" valor={radicado} />
        <Dato icono={ICONO_CALENDARIO} etiqueta="Fecha Radicado SIAF" valor={formatDate(fechaRadicado)} />
        <Dato
          icono={ICONO_CALENDARIO}
          etiqueta="Requiere Medida Preventiva"
          valor={requiereMedida ? "Sí" : "No"}
        />
        <div className="space-y-4">
          <button
            onClick={onViewFile}
            className="btn btn-success btn-sm gap-1 px-2 tooltip"
            data-tip="Ver documento PDF"
          >
            <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
              <path d="M14,2H6A2,2 0 0,0 4,4V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V8L14,2M15.5,15.5L13,19L11.5,15.5L8,14L11.5,12.5L13,9L14.5,12.5L18,14L15.5,15.5M13,3.5L17.5,8H13V3.5Z" />
            </svg>
            <span className="text-xs font-medium text-white">Documento SIAF</span>
          </button>
        </div>
      </div>
    );
  }

  if (isEditable) return null;

  return (
    <div className="text-center py-12">
      <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4 mx-auto">
        <svg className="w-8 h-8 text-base-content/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
          />
        </svg>
      </div>
      <h3 className="text-lg font-medium text-base-content/70 mb-2">Sin medida registrada</h3>
      <p className="text-base-content/60">
        No hay información de medida preventiva para este expediente
      </p>
    </div>
  );
}
