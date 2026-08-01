import { useState } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";

type Decision = {
  id: number;
  tipo_sancion_id: number;
  detalle: string;
};

type Props = {
  data: Decision | undefined;
  tipoSancion: { id: number; nombre: string }[];
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

export default function DecisionFondoData({
  data,
  tipoSancion,
  setToast,
  etapaId,
  expedienteId,
  onDataUpdated,
  isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(!data && isEditable);
  const [isLoading, setIsLoading] = useState(false);

  const getTipoNombre = (idTipo: number) => {
    return tipoSancion.find((t) => t.id === idTipo)?.nombre || "No definido";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const formData = new FormData(e.target as HTMLFormElement);

      const decisionData = {
        tipo_sancion_id: Number(formData.get("tipo_sancion_id")),
        detalle: (formData.get("detalle") as string).trim(),
        etapa_id: etapaId,
      };

      let res;
      if (data?.id) {
        res = await apiCall(
          API_CONFIG.ENDPOINTS.FILE_DECISION_UPDATE(expedienteId),
          {
            method: "PUT",
            body: JSON.stringify(decisionData),
          }
        );
      } else {
        res = await apiCall(API_CONFIG.ENDPOINTS.FILE_DECISION_CREATE(expedienteId), {
          method: "POST",
          body: JSON.stringify(decisionData),
        });
      }

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: data?.id ? "Decisión actualizada" : "Decisión registrada",
          type: "success",
        });
        setShowForm(false);

        if (onDataUpdated) {
          onDataUpdated();
        }
      } else {
        setToast({
          id: Date.now(),
          message: res.detail || "Error al guardar",
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
    if (data) {
      setShowForm(false);
    }
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-error/10 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-error"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold">Decisión de Fondo</h3>
              <p className="text-sm text-base-content/60">
                {data
                  ? "Información de la decisión de fondo"
                  : isEditable
                  ? "Registra una nueva decisión"
                  : "No hay decisión registrada"}
              </p>
            </div>
          </div>
          {!showForm && data && isEditable && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-error hover:bg-error/10"
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

        {!showForm && data && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
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
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Tipo de Sanción
                  </p>
                  <p className="text-sm font-semibold">
                    {getTipoNombre(data.tipo_sancion_id)}
                  </p>
                </div>
              </div>
            </div>

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
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Detalle de la Decisión
                  </p>
                  <p className="text-sm mt-1">{data.detalle}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {!showForm && !data && !isEditable && (
          <div className="text-center py-8 bg-base-200 rounded-lg border-2 border-dashed border-base-300">
            <div className="w-16 h-16 bg-base-300 rounded-full flex items-center justify-center mb-4 mx-auto">
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
              Sin decisión registrada
            </h3>
            <p className="text-base-content/60">
              No hay información de decisión de fondo para este expediente
            </p>
          </div>
        )}

        {showForm && isEditable && (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 gap-6">
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">
                    Tipo de Sanción
                  </span>
                </label>
                <select
                  name="tipo_sancion_id"
                  defaultValue={data?.tipo_sancion_id || ""}
                  className="select select-bordered w-full"
                  required
                  disabled={isLoading}
                >
                  <option value="" disabled>
                    Seleccione un tipo
                  </option>
                  {tipoSancion.map((tipo) => (
                    <option key={tipo.id} value={tipo.id}>
                      {tipo.nombre}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">
                    Detalle de la Decisión
                  </span>
                </label>
                <textarea
                  name="detalle"
                  defaultValue={data?.detalle || ""}
                  className="textarea textarea-bordered w-full h-24"
                  placeholder="Describa la decisión tomada..."
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
              {data && (
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
                className="btn btn-error text-white gap-2"
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
                    {data ? "Guardar Cambios" : "Registrar Decisión"}
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
