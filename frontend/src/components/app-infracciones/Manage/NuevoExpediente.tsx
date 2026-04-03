import type { Expediente, Quejoso } from "../../../types/infraccionApp";
import type { Municipio, ModeloGenerico } from "../../../types/common";
import { useState, useRef } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";

type NewFileProps = {
  userId: number;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  quejosoList: Quejoso[];
  setQuejosoList: (quejosos: Quejoso[]) => void;
  causaList: ModeloGenerico[];
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  onCancel: () => void;
  agregarExpediente: (expediente: Expediente) => void;
};

export default function NewFile({
  userId,
  municipioList,
  recursoAfectadoList,
  quejosoList,
  setQuejosoList,
  causaList,
  setToast,
  onCancel,
  agregarExpediente,
}: NewFileProps) {
  const [sidewalkList, setSidewalkList] = useState<ModeloGenerico[]>([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [recursosSeleccionados, setRecursosSeleccionados] = useState<number[]>(
    [],
  );
  const [quejosoSeleccionado, setQuejosoSeleccionado] = useState<number[]>([]);
  const [showQuejosoModal, setShowQuejosoModal] = useState(false);
  const [quejosoSearch, setQuejosoSearch] = useState("");
  const [newQuejosoNombre, setNewQuejosoNombre] = useState("");
  const [newQuejosoTelefono, setNewQuejosoTelefono] = useState("");
  const [newQuejosoCorreo, setNewQuejosoCorreo] = useState("");
  const [radicadosAsociados, setRadicadosAsociados] = useState<string[]>([""]);
  const [isCreatingQuejoso, setIsCreatingQuejoso] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);

  const quejososFiltrados = quejosoList.filter((q) =>
    q.nombre.toLowerCase().includes(quejosoSearch.toLowerCase()),
  );

  const toggleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const municipioId = Number(e.target.value);
    const municipio = municipioList.find((m) => m.id === municipioId);
    setSidewalkList(municipio?.veredas ?? []);

    if (formRef.current) {
      const veredaEl = formRef.current.elements.namedItem(
        "vereda",
      ) as HTMLSelectElement | null;
      if (veredaEl) veredaEl.value = "";
    }
  };

  const onSubmit = async (payload: any, municipioId: number) => {
    setIsSubmitting(true);
    try {
      const res = await apiCall(API_CONFIG.ENDPOINTS.INFRACTION_ADD, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (res.ok) {
        const expedienteId = res.expediente_id;
        setToast({
          id: Date.now(),
          message: "Expediente registrado",
          type: "success",
        });

        const municipioObj = municipioList.find((m) => m.id === municipioId);

        const nuevoExpediente: Expediente = {
          id: expedienteId,
          radicado: payload.radicado as string,
          fecha_radicado: (payload.fecha_radicado as string) || "",
          municipio: municipioObj
            ? { id: municipioObj.id, nombre: municipioObj.nombre }
            : { id: 0, nombre: "Desconocido" },
          fecha_creacion: new Date().toISOString(),
          involucrados: [],
          archivado: false,
        };

        agregarExpediente(nuevoExpediente);

        formRef.current?.reset();
        setErrorMsg("");
        setSidewalkList([]);
        setRecursosSeleccionados([]);
        setQuejosoSeleccionado([]);
        setRadicadosAsociados([""]);
        onCancel();
      } else {
        /* console.log("Error en respuesta:", res); */
        setErrorMsg(res.detail || "Error al registrar el expediente");
      }
    } catch (e) {
      /* console.error("Error en onSubmit:", e); */
      setErrorMsg("Error de conexión con el servidor");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRecursoToggle = (id: number) => {
    setRecursosSeleccionados((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id],
    );
  };

  const handleQuejosoToggle = (id: number) => {
    setQuejosoSeleccionado((prev) =>
      prev.includes(id) ? prev.filter((q) => q !== id) : [...prev, id],
    );
  };

  const handleCreateQuejoso = async () => {
    if (!newQuejosoNombre.trim()) {
      setToast({
        id: Date.now(),
        message: "El nombre del quejoso es obligatorio",
        type: "error",
      });
      return;
    }

    setIsCreatingQuejoso(true);
    try {
      const res = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_CREATE_COMPLAINER,
        {
          method: "POST",
          body: JSON.stringify({
            nombre: newQuejosoNombre.trim(),
            telefono: newQuejosoTelefono.trim() || null,
            correo: newQuejosoCorreo.trim() || null,
          }),
        },
      );

      if (!res.ok || !res.data) {
        setToast({
          id: Date.now(),
          message: res.detail || "No se pudo crear el quejoso",
          type: "error",
        });
        return;
      }

      const nuevoQuejoso = res.data as Quejoso;
      setQuejosoList([...quejosoList, nuevoQuejoso]);
      setQuejosoSeleccionado((prev) =>
        prev.includes(nuevoQuejoso.id) ? prev : [...prev, nuevoQuejoso.id],
      );

      setNewQuejosoNombre("");
      setNewQuejosoTelefono("");
      setNewQuejosoCorreo("");

      setToast({
        id: Date.now(),
        message: "Quejoso creado y seleccionado",
        type: "success",
      });
    } catch {
      setToast({
        id: Date.now(),
        message: "Error de conexión al crear quejoso",
        type: "error",
      });
    } finally {
      setIsCreatingQuejoso(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);

    if (recursosSeleccionados.length === 0) {
      setErrorMsg("Seleccione al menos un recurso afectado");
      return;
    }

    if (quejosoSeleccionado.length === 0) {
      setErrorMsg("Seleccione al menos un quejoso");
      return;
    }

    setErrorMsg("");

    const causaId = Number(formData.get("causa_id"));
    const descripcion = formData.get("descripcion");
    const municipioId = Number(formData.get("municipio"));
    const veredaId = Number(formData.get("vereda"));
    const radicadosAsociadosLimpios = radicadosAsociados
      .map((r) => r.trim())
      .filter((r) => r.length > 0);
    const payload = {
      radicado: formData.get("radicado"),
      fecha_radicado: formData.get("fecha_radicado"),
      direccion: formData.get("direccion"),
      descripcion,
      causa_id: Number.isNaN(causaId) ? null : causaId,
      vereda_id: veredaId,
      abogado_responsable_id: userId,
      recursos_ids: recursosSeleccionados,
      quejosos_ids: quejosoSeleccionado,
      radicados_asociados: radicadosAsociadosLimpios,
    };

    await onSubmit(payload, municipioId);
  };

  const handleAddRadicadoAsociado = () => {
    setRadicadosAsociados((prev) => [...prev, ""]);
  };

  const handleRemoveRadicadoAsociado = (index: number) => {
    setRadicadosAsociados((prev) =>
      prev.length === 1 ? [""] : prev.filter((_, i) => i !== index),
    );
  };

  const handleRadicadoAsociadoChange = (index: number, value: string) => {
    setRadicadosAsociados((prev) =>
      prev.map((item, i) => (i === index ? value.toUpperCase() : item)),
    );
  };

  const handleCancelClick = () => {
    formRef.current?.reset();
    setSidewalkList([]);
    setRecursosSeleccionados([]);
    setQuejosoSeleccionado([]);
    setRadicadosAsociados([""]);
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
              maxLength={15}
              pattern="^\d{4}(IE|EE|ER)\d{4}$"
              title="Debe tener el formato: 4 números + IE o EE o ER + 4 números (ej: 2015IE5678)"
            />
          </div>

          {/* Fecha de Radicado */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Fecha de Radicado *
              </span>
            </label>
            <input
              type="date"
              name="fecha_radicado"
              className="input input-bordered w-full"
              required
              disabled={isSubmitting}
            />
          </div>

          {/* Quejosos */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">Quejosos *</span>
            </label>
            <div className="bg-base-200 rounded-lg p-4 border border-base-300 space-y-3">
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => setShowQuejosoModal(true)}
                disabled={isSubmitting}
              >
                Seleccionar o crear quejoso
              </button>

              {quejosoSeleccionado.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {quejosoList
                    .filter((q) => quejosoSeleccionado.includes(q.id))
                    .map((q) => (
                      <span
                        key={q.id}
                        className="badge badge-success badge-outline p-3"
                      >
                        {q.nombre}
                      </span>
                    ))}
                </div>
              ) : (
                <p className="text-sm text-base-content/60">
                  No hay quejosos seleccionados
                </p>
              )}
            </div>
            {errorMsg && quejosoSeleccionado.length === 0 && (
              <label className="label">
                <span className="label-text-alt text-error">{errorMsg}</span>
              </label>
            )}
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
              {municipioList.map((town) => (
                <option value={town.id} key={town.id}>
                  {town.nombre}
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
                  {sw.nombre}
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

          {/* Causa */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">Causa *</span>
            </label>
            <select
              name="causa_id"
              defaultValue=""
              className="select select-bordered w-full"
              required
              disabled={isSubmitting}
            >
              <option value="" disabled>
                Seleccione una causa
              </option>
              {causaList.map((causa) => (
                <option value={causa.id} key={causa.id}>
                  {causa.nombre}
                </option>
              ))}
            </select>
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
                {recursoAfectadoList.map((r) => (
                  <label
                    key={r.id}
                    className="flex items-center gap-3 p-3 bg-base-100 rounded-lg border border-base-300 hover:border-success cursor-pointer transition-colors"
                  >
                    <input
                      type="checkbox"
                      value={r.id}
                      checked={recursosSeleccionados.includes(r.id)}
                      onChange={() => handleRecursoToggle(r.id)}
                      className="checkbox checkbox-success checkbox-white-check checkbox-sm"
                      disabled={isSubmitting}
                    />
                    <span className="text-sm font-medium text-base-content">
                      {r.nombre}
                    </span>
                  </label>
                ))}
              </div>
            </div>
            {errorMsg && recursosSeleccionados.length === 0 && (
              <label className="label">
                <span className="label-text-alt text-error">{errorMsg}</span>
              </label>
            )}
          </div>

          {/* Radicados Asociados */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Radicados Asociados
              </span>
            </label>
            <div className="space-y-2">
              {radicadosAsociados.map((radicado, index) => (
                <div key={index} className="flex gap-2">
                  <input
                    type="text"
                    value={radicado}
                    onChange={(e) =>
                      handleRadicadoAsociadoChange(index, e.target.value)
                    }
                    placeholder="Ej: 2015IE5678"
                    className="input input-bordered w-full"
                    disabled={isSubmitting}
                    maxLength={15}
                    pattern="^$|^\d{4}(IE|EE|ER)\d{4}$"
                    title="Debe tener el formato: 4 números + IE o EE o ER + 4 números (ej: 2015IE5678)"
                  />
                  <button
                    type="button"
                    className="btn btn-outline btn-error"
                    onClick={() => handleRemoveRadicadoAsociado(index)}
                    disabled={isSubmitting}
                    title="Eliminar radicado"
                  >
                    <i className="bx bx-trash"></i>
                  </button>
                </div>
              ))}
            </div>

            <div className="mt-2">
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={handleAddRadicadoAsociado}
                disabled={isSubmitting}
              >
                + Agregar radicado
              </button>
            </div>
          </div>

          {/* Descripción */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">Descripción *</span>
            </label>
            <textarea
              name="descripcion"
              placeholder="Describa el expediente"
              className="textarea textarea-bordered w-full h-24 resize-none"
              required
              disabled={isSubmitting}
              maxLength={300}
            />
            <label className="label">
              <span className="label-text-alt text-base-content/60">
                Máximo 300 caracteres
              </span>
            </label>
          </div>

          {/* Error general */}
          {errorMsg && recursosSeleccionados.length > 0 && (
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

      {showQuejosoModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-2xl rounded-xl bg-base-100 shadow-2xl border border-base-300 max-h-[85vh] overflow-hidden">
            <div className="p-4 border-b border-base-300 flex items-center justify-between">
              <h3 className="text-lg font-semibold">Quejosos</h3>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowQuejosoModal(false)}
              >
                Cerrar
              </button>
            </div>

            <div className="p-4 space-y-4 overflow-y-auto max-h-[70vh]">
              <div className="form-control">
                <input
                  type="text"
                  className="input input-bordered"
                  placeholder="Buscar quejoso por nombre"
                  value={quejosoSearch}
                  onChange={(e) => setQuejosoSearch(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                {quejososFiltrados.length === 0 ? (
                  <p className="text-sm text-base-content/60">
                    No hay quejosos para mostrar
                  </p>
                ) : (
                  quejososFiltrados.map((q) => (
                    <label
                      key={q.id}
                      className="flex items-center gap-3 p-3 rounded-lg border border-base-300"
                    >
                      <input
                        type="checkbox"
                        className="checkbox checkbox-success checkbox-sm"
                        checked={quejosoSeleccionado.includes(q.id)}
                        onChange={() => handleQuejosoToggle(q.id)}
                      />
                      <div className="text-sm">
                        <p className="font-medium">{q.nombre}</p>
                        {q.correo && (
                          <p className="text-base-content/60">{q.correo}</p>
                        )}
                      </div>
                    </label>
                  ))
                )}
              </div>

              <div className="divider">Crear nuevo quejoso</div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <input
                  type="text"
                  className="input input-bordered"
                  placeholder="Nombre"
                  value={newQuejosoNombre}
                  onChange={(e) => setNewQuejosoNombre(e.target.value)}
                />
                <input
                  type="text"
                  className="input input-bordered"
                  placeholder="Teléfono"
                  value={newQuejosoTelefono}
                  onChange={(e) => setNewQuejosoTelefono(e.target.value)}
                />
                <input
                  type="email"
                  className="input input-bordered"
                  placeholder="Correo"
                  value={newQuejosoCorreo}
                  onChange={(e) => setNewQuejosoCorreo(e.target.value)}
                />
              </div>

              <div className="flex justify-end">
                <button
                  type="button"
                  className="btn btn-success text-white"
                  onClick={handleCreateQuejoso}
                  disabled={isCreatingQuejoso}
                >
                  {isCreatingQuejoso ? (
                    <>
                      <span className="loading loading-spinner loading-sm"></span>
                      Creando...
                    </>
                  ) : (
                    "Crear quejoso"
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
