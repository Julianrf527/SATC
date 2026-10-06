import type { ExpedienteDetalle, Quejoso, TipoAfectacion } from "../types";
import type { Municipio, ModeloGenerico } from "@shared/types/common";
import { API_CONFIG } from "@shared/lib/api";
import Informacion from "./informacion/InformacionInfraccionData";
import { InvolucradosExpediente } from "@features/involucrados-expediente";
import AlertasInfraccion from "./informacion/AlertasInfraccion";
import { useInvalidarExpediente } from "../api/invalidar";

type Props = {
  expediente: ExpedienteDetalle | null;
  municipioList?: Municipio[];
  recursoAfectadoList?: ModeloGenerico[];
  tipoAfectacionList?: TipoAfectacion[];
  quejosoList?: Quejoso[];
  setQuejosoList?: (quejosos: Quejoso[]) => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
};

export default function InformationInfraccion({
  expediente,
  municipioList,
  recursoAfectadoList,
  tipoAfectacionList,
  quejosoList,
  setQuejosoList,
  setToast,
  isEditable = true,
}: Props) {
  // Vincular/desvincular involucrados cambia el estado del expediente.
  const invalidarExpediente = useInvalidarExpediente(expediente?.id ?? 0);

  if (!expediente) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <div className="w-16 h-16 bg-base-200 rounded-full flex items-center justify-center mb-4 mx-auto">
            <svg
              className="w-8 h-8 text-base-content/40"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-base-content/70 mb-2">
            Sin expediente seleccionado
          </h3>
          <p className="text-base-content/60">
            Selecciona un expediente para ver su información
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="w-full">
        <Informacion
          expediente={expediente}
          municipioList={municipioList || []}
          recursoAfectadoList={recursoAfectadoList || []}
          tipoAfectacionList={tipoAfectacionList || []}
          quejosoList={quejosoList || []}
          setQuejosoList={setQuejosoList}
          setToast={setToast}
          isEditable={isEditable}
        />
      </div>

      <div className="w-full">
        <InvolucradosExpediente
          expedienteId={expediente.id}
          involucradosList={expediente.involucrados}
          onInvolucradosUpdate={() => void invalidarExpediente()}
          endpoints={{
            listar: API_CONFIG.ENDPOINTS.INFRACTION_INVOLVED_LIST,
            vincular: API_CONFIG.ENDPOINTS.INFRACTION_INVOLVED_LINK,
            desvincular: (id) =>
              `${API_CONFIG.ENDPOINTS.INFRACTION_INVOLVED_UNLINK(id)}?expediente_id=${expediente.id}`,
          }}
          setToast={setToast}
          isEditable={isEditable}
        />
      </div>

      {/* Alertas solo visibles en modo editable */}
      {isEditable && (
        <div className="w-full">
          <AlertasInfraccion
            expediente_id={expediente.id}
            setToast={setToast}
          />
        </div>
      )}
    </div>
  );
}
