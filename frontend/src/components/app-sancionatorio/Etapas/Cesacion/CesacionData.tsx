import { useState } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";

type Cesacion = {
  id: number;
  tipo_cesacion_id: number;
};

type Props = {
  data?: Cesacion | null;
  tipoMedida: { id: number; nombre: string }[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  etapaId: number;
  expedienteId: number;
  onDataUpdated?: () => void;
  isEditable?: boolean;
};

export default function CesacionData({
  data,
  tipoMedida,
  setToast,
  etapaId,
  expedienteId,
  onDataUpdated,
  isEditable = true,
}: Props) {
  // Solo considerar que hay cesación si tiene ID
  const hasCesacion = data && data.id;
  const [localData, setLocalData] = useState<Cesacion | null>(
    hasCesacion ? data : null
  );
  const [showForm, setShowForm] = useState(!hasCesacion && isEditable);
  const [isLoading, setIsLoading] = useState(false);

  const getTipoNombre = (idTipo: number) => {
    return tipoMedida.find((t) => t.id === idTipo)?.nombre || "No definido";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const formData = new FormData(e.target as HTMLFormElement);
      const tipoCesacionId = Number(formData.get("tipo_cesacion_id"));

      const cesacionData = {
        tipo_cesacion_id: tipoCesacionId,
        etapa_id: etapaId,
      };

      let res;
      if (localData?.id) {
        res = await apiCall(
          API_CONFIG.ENDPOINTS.FILE_CESSATION_UPDATE(expedienteId),
          {
            method: "PUT",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(cesacionData),
          }
        );
      } else {
        res = await apiCall(API_CONFIG.ENDPOINTS.FILE_CESSATION_CREATE(expedienteId), {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(cesacionData),
        });
      }

      if (res.ok) {
        const updatedData: Cesacion = {
          id: res.id || localData?.id || 0,
          tipo_cesacion_id: tipoCesacionId,
        };
        setLocalData(updatedData);

        setToast({
          id: Date.now(),
          message:
            res.message ||
            (localData?.id ? "Cesación actualizada" : "Cesación registrada"),
          type: "success",
        });
        setShowForm(false);

        if (onDataUpdated) {
          onDataUpdated();
        }
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || res.message || "Error al guardar",
          type: "error",
        });
      }
    } catch (error) {
      setToast({
        id: Date.now(),
        message: "Error al procesar la solicitud",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    if (localData) {
      setShowForm(false);
    }
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-info/10 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-info"
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
            <div>
              <h3 className="text-xl font-bold">Tipo de Cesación</h3>
              <p className="text-sm text-base-content/60">
                {localData
                  ? "Información del tipo de cesación aplicada"
                  : isEditable
                  ? "Registra el tipo de cesación"
                  : "No hay cesación registrada"}
              </p>
            </div>
          </div>
          {!showForm && localData && isEditable && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-info hover:bg-info/10"
              onClick={() => setShowForm(true)}
              disabled={isLoading}
            >
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                />
              </svg>
              Editar
            </button>
          )}
        </div>

        {!showForm && localData && (
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 bg-base-200 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                <svg
                  className="w-4 h-4 text-base-content/70"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                  />
                </svg>
              </div>
              <div>
                <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                  Tipo de Cesación
                </p>
                <p className="text-sm font-semibold mt-1">
                  {getTipoNombre(localData.tipo_cesacion_id)}
                </p>
              </div>
            </div>
          </div>
        )}

        {!showForm && !localData && !isEditable && (
          <div className="text-center py-12">
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
              Sin cesación registrada
            </h3>
            <p className="text-base-content/60">
              No hay información de tipo de cesación para este expediente
            </p>
          </div>
        )}

        {showForm && isEditable && (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Tipo de Cesación <span className="text-error">*</span>
                </span>
              </label>
              <select
                name="tipo_cesacion_id"
                defaultValue={localData?.tipo_cesacion_id || ""}
                className="select select-bordered w-full"
                required
                disabled={isLoading}
              >
                <option value="" disabled>
                  Seleccione un tipo
                </option>
                {tipoMedida.map((tipo) => (
                  <option key={tipo.id} value={tipo.id}>
                    {tipo.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
              {localData && (
                <button
                  type="button"
                  onClick={handleCancel}
                  className="btn btn-outline"
                  disabled={isLoading}
                >
                  Cancelar
                </button>
              )}
              <button
                type="submit"
                className="btn btn-info text-white gap-2"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="loading loading-spinner loading-sm"></span>
                    Guardando...
                  </>
                ) : (
                  <>
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    {localData ? "Guardar Cambios" : "Registrar Cesación"}
                  </>
                )}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
