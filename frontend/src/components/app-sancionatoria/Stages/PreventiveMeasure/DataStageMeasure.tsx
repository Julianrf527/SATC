import { useState } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";

type Medida = {
  id: number;
  tipo_medida_id: number;
  cantidad: string;
  especie: string;
  estado_medida: boolean | null;
};

type Props = {
  data?: Medida | null;
  etapaId: number;
  tipoMedida: { id: number; nombre: string }[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
};

export default function DataStageMeasure({
  data,
  etapaId,
  tipoMedida,
  setToast,
  isEditable = true,
}: Props) {
  // Solo considerar que hay medida si tiene ID
  const hasMedida = data && data.id;
  const [medida, setMedida] = useState<Medida | null>(hasMedida ? data : null);
  const [showForm, setShowForm] = useState(!hasMedida && isEditable);
  const [isLoading, setIsLoading] = useState(false);

  const parseCantidad = (cantidad?: string) => {
    if (!cantidad) return { valor: "", unidad: "" };
    const parts = cantidad.trim().split(" ");
    if (parts.length === 2) {
      return { valor: parts[0], unidad: parts[1] };
    }
    return { valor: cantidad, unidad: "" };
  };

  const getTipoNombre = (idTipo: number) => {
    return tipoMedida.find((t) => t.id === idTipo)?.nombre || "No definido";
  };

  const getEstadoLabel = (estado: boolean | null) => {
    if (estado === null) return "No Aplica";
    return estado ? "Vigente" : "Levantada";
  };

  const getEstadoBadgeClass = (estado: boolean | null) => {
    if (estado === null) return "badge-ghost";
    return estado ? "badge-success" : "badge-warning";
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const formData = new FormData(e.target as HTMLFormElement);

      const estadoValue = formData.get("estado_medida") as string;
      let estadoBoolean: boolean | null = null;

      if (estadoValue === "true") estadoBoolean = true;
      else if (estadoValue === "false") estadoBoolean = false;
      else if (estadoValue === "null") estadoBoolean = null;

      // Componer la cantidad con valor + unidad
      const cantidadValor = formData.get("cantidad_valor") as string;
      const cantidadUnidad = formData.get("cantidad_unidad") as string;
      const cantidadCompleta = `${cantidadValor} ${cantidadUnidad}`;

      const medidaData = {
        tipo_medida_id: Number(formData.get("id_tipo")),
        cantidad: cantidadCompleta,
        especie: (formData.get("especie") as string).trim(),
        estado_medida: estadoBoolean,
        etapa_id: etapaId,
      };

      if (medida) {
        console.log("Actualizar medida:", medidaData);
        const response = await apiCall(
          API_CONFIG.ENDPOINTS.FILE_MEASURE_UPDATE(medida.id),
          {
            method: "PUT",
            body: JSON.stringify(medidaData),
          }
        );

        if (response.ok) {
          const updatedMedida: Medida = {
            ...medida,
            tipo_medida_id: medidaData.tipo_medida_id,
            cantidad: medidaData.cantidad,
            especie: medidaData.especie,
            estado_medida: medidaData.estado_medida,
          };
          setMedida(updatedMedida);
          setToast({
            id: Date.now(),
            message: "Medida actualizada exitosamente",
            type: "success",
          });
          setShowForm(false);
        } else {
          setToast({
            id: Date.now(),
            message: response.detail || "Error al actualizar la medida",
            type: "error",
          });
        }
      } else {
        // CREAR nueva medida
        const response = await apiCall(
          API_CONFIG.ENDPOINTS.FILE_MEASURE_CREATE,
          {
            method: "POST",
            body: JSON.stringify(medidaData),
          }
        );

        if (response.ok) {
          const newMedida: Medida = {
            id: response.id,
            tipo_medida_id: medidaData.tipo_medida_id,
            cantidad: medidaData.cantidad,
            especie: medidaData.especie,
            estado_medida: medidaData.estado_medida,
          };
          setMedida(newMedida);
          setToast({
            id: Date.now(),
            message: "Medida registrada exitosamente",
            type: "success",
          });
          setShowForm(false);
        } else {
          const errorMessage = Array.isArray(response.detail)
            ? response.detail
                .map((e: any) => `${e.loc.join(".")}: ${e.msg}`)
                .join(", ")
            : response.detail || "Error al registrar la medida";
          setToast({ id: Date.now(), message: errorMessage, type: "error" });
        }
      }
    } catch (error) {
      console.error("Error al guardar:", error);
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
    if (medida) {
      setShowForm(false);
    }
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        {/* HEADER */}
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
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold">Datos de la Medida</h3>
              <p className="text-sm text-base-content/60">
                {medida
                  ? "Información de la medida aplicada"
                  : isEditable
                  ? "Registra una nueva medida"
                  : "No hay medida registrada"}
              </p>
            </div>
          </div>
          {!showForm && medida && isEditable && (
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

        {/* VISTA DE DATOS */}
        {!showForm && medida && (
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
                      d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Tipo de Medida
                  </p>
                  <p className="text-sm font-semibold">
                    {getTipoNombre(medida.tipo_medida_id)}
                  </p>
                </div>
              </div>

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
                      d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Cantidad
                  </p>
                  <p className="text-sm">{medida.cantidad}</p>
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
                      d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Especie
                  </p>
                  <p className="text-sm">{medida.especie}</p>
                </div>
              </div>

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
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Estado de la Medida
                  </p>
                  <span
                    className={`badge text-white ${getEstadoBadgeClass(
                      medida.estado_medida
                    )} badge-sm mt-1`}
                  >
                    {getEstadoLabel(medida.estado_medida)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* MENSAJE CUANDO NO HAY MEDIDA Y NO ES EDITABLE */}
        {!showForm && !medida && !isEditable && (
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
                  d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-base-content/70 mb-2">
              Sin medida registrada
            </h3>
            <p className="text-base-content/60">
              No hay información de medida preventiva para este expediente
            </p>
          </div>
        )}

        {/* FORMULARIO DE EDICIÓN/REGISTRO - Solo si isEditable */}
        {showForm && isEditable && (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Tipo de Medida */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Tipo de Medida</span>
                </label>
                <select
                  name="id_tipo"
                  defaultValue={medida?.tipo_medida_id || ""}
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

              {/* Cantidad */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Cantidad</span>
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    name="cantidad_valor"
                    defaultValue={parseCantidad(medida?.cantidad).valor}
                    className="input input-bordered w-2/3"
                    placeholder="0"
                    step="0.01"
                    min="0"
                    required
                    disabled={isLoading}
                  />
                  <select
                    name="cantidad_unidad"
                    defaultValue={parseCantidad(medida?.cantidad).unidad}
                    className="select select-bordered w-1/3"
                    required
                    disabled={isLoading}
                  >
                    <option value="">Unidad</option>
                    <option value="m³">m³</option>
                    <option value="L">Litros</option>
                    <option value="m²">m²</option>
                    <option value="Ha">Hectáreas</option>
                    <option value="kg">Kilogramos</option>
                    <option value="ton">Toneladas</option>
                    <option value="und">Unidades</option>
                    <option value="m">Metros</option>
                    <option value="km">Kilómetros</option>
                  </select>
                </div>
              </div>

              {/* Especie */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Especie</span>
                </label>
                <input
                  type="text"
                  name="especie"
                  defaultValue={medida?.especie || ""}
                  className="input input-bordered w-full"
                  required
                  disabled={isLoading}
                />
              </div>

              {/* Estado */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">
                    Estado de la Medida
                  </span>
                </label>
                <select
                  name="estado_medida"
                  defaultValue={
                    medida?.estado_medida === null
                      ? "null"
                      : medida?.estado_medida?.toString() || "null"
                  }
                  className="select select-bordered w-full"
                  required
                  disabled={isLoading}
                >
                  <option value="true">Vigente</option>
                  <option value="false">Levantada</option>
                  <option value="null">No Aplica</option>
                </select>
              </div>
            </div>

            {/* Botones */}
            <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
              {medida && (
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
                    {medida ? "Guardar Cambios" : "Registrar Medida"}
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
