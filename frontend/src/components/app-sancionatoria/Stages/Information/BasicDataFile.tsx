import React, { useState, useRef, useEffect } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import type { File, Town, Resource } from "../../../../types";

interface Props {
  file: File;
  towns: Town[];
  resources: Resource[];
  onFileUpdate?: (updatedFile: File) => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
}

export default function BasicDataFile({
  file,
  towns,
  resources,
  onFileUpdate,
  setToast,
  isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedResources, setSelectedResources] = useState<number[]>(
    file.recurso_afectado || []
  );
  const [sidewalkList, setSidewalkList] = useState<
    { id: number; name: string }[]
  >([]);
  const formRef = useRef<HTMLFormElement | null>(null);

  useEffect(() => {
    const town = towns.find((t) =>
      t.sidewalk.some((s) => s.id === file.vereda?.id)
    );
    setSidewalkList(town?.sidewalk || []);
  }, [file, towns]);

  const handleResourceToggle = (id: number) => {
    setSelectedResources((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    );
  };

  const toggleChangeTown = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const townId = Number(e.target.value);
    const town = towns.find((t) => t.id === townId);
    setSidewalkList(town?.sidewalk || []);
  };

  const validateForm = () => {
    if (selectedResources.length === 0) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar al menos un recurso afectado",
        type: "error",
      });
      return false;
    }
    return true;
  };

  const hasDataChanged = (formData: FormData): boolean => {
    const newRadicado = formData.get("radicado") as string;
    const newNombre = formData.get("nombre") as string;
    const newMotivo = formData.get("motivo") as string;
    const newDireccion = formData.get("direccion") as string;
    const newVeredaId = Number(formData.get("vereda"));
    const newMunicipioId = Number(formData.get("municipio"));

    const resourcesChanged =
      JSON.stringify([...selectedResources].sort()) !==
      JSON.stringify([...(file.recurso_afectado || [])].sort());

    return (
      newRadicado !== file.radicado ||
      newNombre !== file.nombre ||
      newMotivo !== (file.motivo_afectacion || "") ||
      newDireccion !== file.direccion ||
      newVeredaId !== (file.vereda?.id || 0) ||
      newMunicipioId !== file.municipio.id ||
      resourcesChanged
    );
  };

  const updateExpediente = async (updatedFile: File): Promise<boolean> => {
    try {
      const updatePayload = {
        radicado: updatedFile.radicado,
        expediente: updatedFile.nombre,
        recurso: updatedFile.recurso_afectado || [],
        motivo: updatedFile.motivo_afectacion || "",
        vereda: updatedFile.vereda?.id || 0,
        direccion: updatedFile.direccion,
      };

      const response = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_BASIC_DATA(file.radicado),
        {
          method: "PUT",
          body: JSON.stringify(updatePayload),
        }
      );

      if (response.ok) {
        setToast({
          id: Date.now(),
          message: "Expediente actualizado exitosamente",
          type: "success",
        });
        return true;
      } else {
        setToast({
          id: Date.now(),
          message: response.detail || "El radicado se encuentra en uso",
          type: "error",
        });
        /* console.error("Error al actualizar expediente:", response.detail); */
        return false;
      }
    } catch (networkError) {
      /* console.error("Error de red o fetch:", networkError); */
      setToast({
        id: Date.now(),
        message: "Error de conexión al actualizar el expediente",
        type: "error",
      });
      return false;
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const formData = new FormData(e.target as HTMLFormElement);

      if (!validateForm()) {
        setIsLoading(false);
        return;
      }

      if (!hasDataChanged(formData)) {
        setShowForm(false);
        setIsLoading(false);
        return;
      }

      const selectedTown = towns.find(
        (t) => t.id === Number(formData.get("municipio"))
      );
      const selectedVereda = sidewalkList.find(
        (s) => s.id === Number(formData.get("vereda"))
      );

      // Crear el File actualizado completo
      const updatedFile: File = {
        ...file,
        radicado: (formData.get("radicado") as string).trim(),
        nombre: (formData.get("nombre") as string).trim(),
        recurso_afectado: selectedResources,
        motivo_afectacion: (formData.get("motivo") as string).trim(),
        direccion: (formData.get("direccion") as string).trim(),
        vereda: {
          id: Number(formData.get("vereda")),
          name: selectedVereda?.name || "",
        },
        municipio: {
          id: Number(formData.get("municipio")),
          name: selectedTown?.name || file.municipio.name,
        },
      };

      const updateSuccess = await updateExpediente(updatedFile);

      if (updateSuccess) {
        // Esperar un momento para que el servidor procese
        await new Promise((resolve) => setTimeout(resolve, 300));

        // Notificar al padre que se actualizó el expediente
        // El padre (FileDetail) se encargará de refrescar desde el servidor
        if (onFileUpdate) {
          await onFileUpdate(updatedFile);
        }

        // Actualizar el estado local de recursos seleccionados
        setSelectedResources(updatedFile.recurso_afectado || []);
        setShowForm(false);
      }
    } catch (error) {
      /* console.error("Error completo al guardar:", error); */

      let errorMessage = "Error desconocido al actualizar el expediente";

      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === "string") {
        errorMessage = error;
      } else if (error && typeof error === "object") {
        if ("message" in error) {
          errorMessage = String(error.message);
        } else if ("detail" in error) {
          errorMessage = String(error.detail);
        } else if ("error" in error) {
          errorMessage = String(error.error);
        }
      }

      setToast({ id: Date.now(), message: errorMessage, type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setSelectedResources(file.recurso_afectado || []);
    setShowForm(false);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-success"
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
              <h3 className="text-xl font-bold">Datos del Expediente</h3>
              <p className="text-sm text-base-content/60">
                Información básica del caso
              </p>
            </div>
          </div>
          {!showForm && isEditable && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-success hover:bg-success/10"
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

        {!showForm && (
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
                      d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Radicado
                  </p>
                  <p className="text-sm font-semibold">{file.radicado}</p>
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
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Expediente
                  </p>
                  <p className="text-sm">{file.nombre}</p>
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
                      d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"
                    />
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Lugar
                  </p>
                  <p className="text-sm">
                    {file.vereda?.name || "No definido"}, {file.municipio.name}
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
                      d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Recursos Afectados
                  </p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {file.recurso_afectado &&
                    file.recurso_afectado.length > 0 ? (
                      file.recurso_afectado
                        .map(
                          (id) =>
                            resources.find((resource) => resource.id === id)
                              ?.name
                        )
                        .filter((name) => name)
                        .map((name, index) => (
                          <span
                            key={index}
                            className="badge badge-success text-white badge-sm"
                          >
                            {name}
                          </span>
                        ))
                    ) : (
                      <span className="text-sm text-base-content/40">
                        Sin recursos asignados
                      </span>
                    )}
                  </div>
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
                      d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Fecha de Creación
                  </p>
                  <p className="text-sm">{formatDate(file.fecha_creacion)}</p>
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
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Última Etapa
                  </p>
                  {file.ultima_etapa ? (
                    <p className="text-sm font-medium text-success">
                      {file.ultima_etapa}
                    </p>
                  ) : (
                    <p className="text-sm text-base-content/40">
                      Sin etapa registrada
                    </p>
                  )}
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
                      d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Dirección
                  </p>
                  <p className="text-sm">{file.direccion}</p>
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
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </div>
                <div>
                  <p className="text-xs font-medium text-base-content/60 uppercase tracking-wide">
                    Motivo de Afectación
                  </p>
                  <p className="text-sm">
                    {file.motivo_afectacion || "Sin motivo especificado"}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {showForm && isEditable && (
          <form ref={formRef} onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Radicado</span>
                </label>
                <input
                  type="text"
                  name="radicado"
                  defaultValue={file.radicado}
                  className="input input-bordered w-full"
                  required
                  disabled={isLoading}
                  pattern="^\d{4}(IE|EE|ER)\d{4}$"
                  title="Debe tener el formato: 4 números + IE o EE o ER + 4 números (ej: 2015IE5678)"
                />
              </div>

              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Expediente</span>
                </label>
                <input
                  type="text"
                  name="nombre"
                  defaultValue={file.nombre}
                  className="input input-bordered w-full"
                  required
                  disabled={isLoading}
                  pattern="^Q\d{3}-\d{2}$"
                  title="Debe tener el formato: Q + 3 números + - + 2 números (ej: Q123-45)"
                />
              </div>

              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Municipio</span>
                </label>
                <select
                  name="municipio"
                  defaultValue={file.municipio?.id || ""}
                  onChange={toggleChangeTown}
                  className="select select-bordered w-full"
                  required
                  disabled={isLoading}
                >
                  <option value="" disabled>
                    Seleccione un municipio
                  </option>
                  {towns.map((t) => (
                    <option value={t.id} key={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Vereda</span>
                </label>
                <select
                  name="vereda"
                  defaultValue={file.vereda?.id || ""}
                  className="select select-bordered w-full"
                  required
                  disabled={isLoading}
                >
                  <option value="" disabled>
                    Seleccione una vereda
                  </option>
                  {sidewalkList.map((sw) => (
                    <option value={sw.id} key={sw.id}>
                      {sw.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Recursos Afectados
                </span>
              </label>
              <div className="bg-base-200 rounded-lg p-4 border border-base-300">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {resources.map((r) => (
                    <label
                      key={r.id}
                      className="flex items-center gap-3 p-3 bg-base-100 rounded-lg border border-base-300 hover:border-success/50 cursor-pointer transition-colors"
                    >
                      <input
                        type="checkbox"
                        value={r.id}
                        checked={selectedResources.includes(r.id)}
                        onChange={() => handleResourceToggle(r.id)}
                        className="checkbox checkbox-success checkbox-sm"
                        disabled={isLoading}
                      />
                      <span className="text-sm font-medium">{r.name}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">Dirección</span>
              </label>
              <input
                type="text"
                name="direccion"
                defaultValue={file.direccion}
                className="input input-bordered w-full"
                required
                disabled={isLoading}
                maxLength={100}
              />
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Motivo de Afectación
                </span>
              </label>
              <textarea
                name="motivo"
                defaultValue={file.motivo_afectacion || ""}
                rows={3}
                className="textarea textarea-bordered resize-none w-full"
                required
                disabled={isLoading}
                maxLength={200}
              />
            </div>

            <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
              <button
                type="button"
                onClick={handleCancel}
                className="btn btn-outline"
                disabled={isLoading}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn btn-success text-white gap-2"
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
                    Guardar Cambios
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
