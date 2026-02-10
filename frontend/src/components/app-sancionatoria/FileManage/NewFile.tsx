import { useState, useRef } from "react";
import type { File, Town, Resource } from "../../../types";
import { apiCall, API_CONFIG } from "../../../utils/api";

type NewFileProps = {
  userId: number;
  towns: Town[];
  resource: Resource[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  onCancel: () => void;
  addFile: (file: File) => void;
};

export default function NewFile({
  userId,
  towns,
  resource,
  setToast,
  onCancel,
  addFile,
}: NewFileProps) {
  const [sidewalkList, setSidewalkList] = useState<Resource[]>([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [selectedResources, setSelectedResources] = useState<number[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);

  const toggleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const townId = Number(e.target.value);
    const town = towns.find((t) => t.id === townId);
    setSidewalkList(town?.sidewalk ?? []);

    if (formRef.current) {
      const veredaEl = formRef.current.elements.namedItem(
        "vereda"
      ) as HTMLSelectElement | null;
      if (veredaEl) veredaEl.value = "";
    }
  };

  const onSubmit = async (formData: any) => {
    setIsSubmitting(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.FILE_ADD, {
        method: "POST",
        body: JSON.stringify(formData),
      });

      if (res.ok) {
        setToast({
          id: Date.now(),
          message: "Expediente registrado",
          type: "success",
        });

        const municipioObj = towns.find(
          (t) => t.id === Number(formData.municipio)
        );
        const veredaObj = municipioObj?.sidewalk.find(
          (sw) => sw.id === Number(formData.vereda)
        );

        const newFile: File = {
          radicado: formData.radicado as string,
          nombre: formData.expediente as string,
          recurso_afectado: selectedResources,
          motivo_afectacion: formData.motivo as string,
          fecha_creacion: new Date().toISOString().split("T")[0],
          direccion: formData.direccion as string,
          municipio: municipioObj
            ? { id: municipioObj.id, name: municipioObj.name }
            : { id: 0, name: "Desconocido" },
          vereda: veredaObj
            ? { id: veredaObj.id, name: veredaObj.name }
            : { id: 0, name: "Desconocido" },
          involucrados: [],
        };

        addFile(newFile);

        formRef.current?.reset();
        setErrorMsg("");
        setSidewalkList([]);
        setSelectedResources([]);
        onCancel();
      } else {
        console.log("Error en respuesta:", res);
        setErrorMsg(res.detail || "Error al registrar el expediente");
      }
    } catch (e) {
      console.error("Error en onSubmit:", e);
      setErrorMsg("Error de conexión con el servidor");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResourceToggle = (id: number) => {
    setSelectedResources((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);

    if (selectedResources.length === 0) {
      setErrorMsg("Seleccione al menos un recurso afectado");
    } else {
      setErrorMsg("");
      const data = {
        radicado: formData.get("radicado"),
        expediente: formData.get("expediente"),
        recurso: selectedResources,
        motivo: formData.get("motivo"),
        encargado_id: userId,
        municipio: formData.get("municipio"),
        vereda: formData.get("vereda"),
        direccion: formData.get("direccion"),
      };

      await onSubmit(data);
    }
  };

  const handleCancelClick = () => {
    formRef.current?.reset();
    setSidewalkList([]);
    setSelectedResources([]);
    setErrorMsg("");
    onCancel();
  };

  return (
    <div className="flex flex-col h-full bg-base-100">
      {/* Header */}
      <div className="flex-shrink-0 p-6 border-b border-base-300">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center">
            <svg
              className="w-5 h-5 text-primary"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
          </div>
          <div>
            <h2 className="text-2xl font-bold text-base-content">
              Nuevo Expediente
            </h2>
            <p className="text-sm text-base-content/60">
              Completa la información del expediente
            </p>
          </div>
        </div>
      </div>

      {/* Formulario scrolleable */}
      <div className="flex-1 overflow-y-auto p-6">
        <form
          ref={formRef}
          onSubmit={handleSubmit}
          id="new-file-form"
          className="space-y-4"
        >
          {/* Radicado */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">Radicado *</span>
            </label>
            <input
              type="text"
              name="radicado"
              placeholder="Ingrese el radicado"
              className="input input-bordered w-full"
              required
              disabled={isSubmitting}
              pattern="^\d{4}(IE|EE|ER)\d{4}$"
              title="Debe tener el formato: 4 números + IE o EE o ER + 4 números (ej: 2015IE5678)"
            />
          </div>

          {/* Expediente */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Numero del Expediente *
              </span>
            </label>
            <input
              type="text"
              name="expediente"
              placeholder="Numero del expediente"
              className="input input-bordered w-full"
              required
              disabled={isSubmitting}
              pattern="^Q\d{3}-\d{2}$"
              title="Debe tener el formato: Q + 3 números + - + 2 números (ej: Q123-45)"
            />
          </div>

          {/* Recursos Afectados */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Recursos Afectados *
              </span>
            </label>
            <div className="bg-base-200 rounded-lg p-4 border border-base-300">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {resource.map((r) => (
                  <label
                    key={r.id}
                    className="flex items-center gap-3 p-3 bg-base-100 rounded-lg border border-base-300 hover:border-success cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      value={r.id}
                      checked={selectedResources.includes(r.id)}
                      onChange={() => handleResourceToggle(r.id)}
                      className="checkbox checkbox-success checkbox-white-check checkbox-sm"
                      disabled={isSubmitting}
                    />
                    <span className="text-sm font-medium text-base-content">
                      {r.name}
                    </span>
                  </label>
                ))}
              </div>
            </div>
            {errorMsg && selectedResources.length === 0 && (
              <label className="label">
                <span className="label-text-alt text-error">{errorMsg}</span>
              </label>
            )}
          </div>

          {/* Motivo de Afectación */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Motivo de Afectación *
              </span>
            </label>
            <textarea
              name="motivo"
              placeholder="Describa el motivo de la afectación"
              className="textarea textarea-bordered w-full h-24 resize-none"
              required
              disabled={isSubmitting}
              maxLength={200}
            />
          </div>

          {/* Municipio */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">Municipio *</span>
            </label>
            <select
              name="municipio"
              defaultValue=""
              onChange={toggleChange}
              className="select select-bordered w-full"
              required
              disabled={isSubmitting}
            >
              <option value="" disabled>
                Seleccione un municipio
              </option>
              {towns.map((town) => (
                <option value={town.id} key={town.id}>
                  {town.name}
                </option>
              ))}
            </select>
          </div>

          {/* Vereda */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">Vereda *</span>
            </label>
            <select
              name="vereda"
              defaultValue=""
              className="select select-bordered w-full"
              required
              disabled={isSubmitting || sidewalkList.length === 0}
            >
              <option value="" disabled>
                {sidewalkList.length === 0
                  ? "Seleccione primero un municipio"
                  : "Seleccione una vereda"}
              </option>
              {sidewalkList.map((sw) => (
                <option value={sw.id} key={sw.id}>
                  {sw.name}
                </option>
              ))}
            </select>
          </div>

          {/* Dirección */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">Dirección *</span>
            </label>
            <input
              type="text"
              name="direccion"
              placeholder="Dirección del predio"
              className="input input-bordered w-full"
              required
              disabled={isSubmitting}
              maxLength={100}
            />
          </div>

          {/* Error general */}
          {errorMsg && selectedResources.length > 0 && (
            <div className="alert alert-error shadow-sm">
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span>{errorMsg}</span>
            </div>
          )}
        </form>
      </div>

      {/* Botones fijos al fondo */}
      <div className="flex-shrink-0 p-6 border-t border-base-300 bg-base-100">
        <div className="flex gap-3 justify-end">
          <button
            type="button"
            className="btn btn-outline"
            onClick={handleCancelClick}
            disabled={isSubmitting}
          >
            Cancelar
          </button>
          <button
            type="submit"
            form="new-file-form"
            className="btn btn-success text-white"
            disabled={isSubmitting}
          >
            {isSubmitting ? (
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
                Agregar Expediente
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
