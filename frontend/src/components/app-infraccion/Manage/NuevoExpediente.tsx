import type {
  Expediente,
  Quejoso,
  TipoAfectacion,
} from "../../../types/infraccionApp";
import type { Municipio, ModeloGenerico } from "../../../types/common";
import { useState, useRef } from "react";
import { apiCall, API_CONFIG } from "../../../utils/api";
import QuejosoSelectorModal from "../Common/QuejosoSelectorModal";

type NewFileProps = {
  userId: number;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  tipoAfectacionList: TipoAfectacion[];
  quejosoList: Quejoso[];
  setQuejosoList: (quejosos: Quejoso[]) => void;
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
  tipoAfectacionList,
  quejosoList,
  setQuejosoList,
  setToast,
  onCancel,
  agregarExpediente,
}: NewFileProps) {
  const [sidewalkList, setSidewalkList] = useState<ModeloGenerico[]>([]);
  const [errorMsg, setErrorMsg] = useState("");
  const [recursosSeleccionados, setRecursosSeleccionados] = useState<number[]>(
    [],
  );
  const [tiposSeleccionados, setTiposSeleccionados] = useState<number[]>([]);
  const [expandedRecursos, setExpandedRecursos] = useState<number[]>([]);
  const [quejosoSeleccionado, setQuejosoSeleccionado] = useState<number[]>([]);
  const [showQuejosoModal, setShowQuejosoModal] = useState(false);
  const [radicadosAsociados, setRadicadosAsociados] = useState<string[]>([""]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const formRef = useRef<HTMLFormElement | null>(null);

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
        setTiposSeleccionados([]);
        setExpandedRecursos([]);
        setQuejosoSeleccionado([]);
        setRadicadosAsociados([""]);
        onCancel();
      } else {
        setErrorMsg(res.detail || "Error al registrar el expediente");
      }
    } catch (e) {
      setErrorMsg("Error de conexión con el servidor");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRecursoToggle = (id: number) => {
    setRecursosSeleccionados((prev) => {
      const next = prev.includes(id)
        ? prev.filter((r) => r !== id)
        : [...prev, id];
      if (!next.includes(id)) {
        const tiposDeEsteRecurso = tipoAfectacionList
          .filter((t) => t.recurso_id === id)
          .map((t) => t.id);
        setTiposSeleccionados((prevTipos) =>
          prevTipos.filter((tid) => !tiposDeEsteRecurso.includes(tid)),
        );
        setExpandedRecursos((prev) => prev.filter((r) => r !== id));
      } else {
        setExpandedRecursos((prev) =>
          prev.includes(id) ? prev : [...prev, id],
        );
      }
      return next;
    });
  };

  const handleToggleExpand = (id: number) => {
    setExpandedRecursos((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id],
    );
  };

  const handleTipoToggle = (id: number) => {
    setTiposSeleccionados((prev) =>
      prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id],
    );
  };

  const handleCreateQuejoso = async (payload: {
    nombre: string | null;
    telefono: string | null;
    correo: string | null;
    anonimo: boolean;
  }) => {
    const res = await apiCall(
      API_CONFIG.ENDPOINTS.INFRACTION_CREATE_COMPLAINER,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );

    if (!res.ok || !res.data) {
      setToast({
        id: Date.now(),
        message: res.detail || "No se pudo crear el quejoso",
        type: "error",
      });
      return null;
    }

    const nuevoQuejoso = res.data as Quejoso;
    setQuejosoList([...quejosoList, nuevoQuejoso]);
    return nuevoQuejoso;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new FormData(e.target as HTMLFormElement);

    if (recursosSeleccionados.length === 0) {
      setErrorMsg("Seleccione al menos un recurso afectado");
      return;
    }

    if (tiposSeleccionados.length === 0) {
      setErrorMsg("Seleccione al menos un tipo de afectación");
      return;
    }

    if (quejosoSeleccionado.length === 0) {
      setErrorMsg("Seleccione al menos un quejoso");
      return;
    }

    setErrorMsg("");

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
      vereda_id: veredaId,
      abogado_responsable_id: userId,
      recursos_ids: recursosSeleccionados,
      tipos_afectacion_ids: tiposSeleccionados,
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
    setTiposSeleccionados([]);
    setExpandedRecursos([]);
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
              maxLength={11}
              pattern="^\d{4}(IE|EE|ER)\d{4,5}$"
              title="Debe tener el formato: 4 números + IE o EE o ER + 4 o 5 números (ej: 2015IE5678)"
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
              max={new Date().toISOString().split("T")[0]}
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
                        className={`badge badge-outline p-3 ${
                          q.anonimo ? "badge-warning" : "badge-success"
                        }`}
                      >
                        {q.anonimo ? "Anónimo" : q.nombre}
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

          {/* Recursos Afectados + Tipos de Afectación */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Recursos Afectados *
              </span>
            </label>
            <div className="border border-base-300 rounded-lg overflow-hidden divide-y divide-base-300">
              {recursoAfectadoList.map((r) => {
                const isSelected = recursosSeleccionados.includes(r.id);
                const isExpanded = expandedRecursos.includes(r.id);
                const tipos = tipoAfectacionList.filter(
                  (t) => t.recurso_id === r.id,
                );
                return (
                  <div key={r.id}>
                    <div
                      className={`flex items-center gap-3 px-4 py-3 transition-colors ${
                        isSelected
                          ? "bg-success/5"
                          : "bg-base-100 hover:bg-base-200"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleRecursoToggle(r.id)}
                        className="checkbox checkbox-success checkbox-sm flex-shrink-0"
                        disabled={isSubmitting}
                      />
                      <span
                        className="flex-1 text-sm font-semibold text-base-content cursor-pointer select-none"
                        onClick={() => handleRecursoToggle(r.id)}
                      >
                        {r.nombre}
                      </span>
                      {tipos.length > 0 && (
                        <button
                          type="button"
                          onClick={() => handleToggleExpand(r.id)}
                          className="btn btn-ghost btn-xs btn-circle"
                          disabled={isSubmitting}
                        >
                          <svg
                            className={`w-4 h-4 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M19 9l-7 7-7-7"
                            />
                          </svg>
                        </button>
                      )}
                    </div>
                    {isExpanded && tipos.length > 0 && (
                      <div className="bg-base-200/50 border-t border-base-300 px-4 py-2 space-y-0.5">
                        {tipos.map((tipo) => (
                          <label
                            key={tipo.id}
                            className={`flex items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                              isSelected
                                ? "hover:bg-base-200"
                                : "opacity-40 cursor-not-allowed"
                            }`}
                          >
                            <input
                              type="checkbox"
                              checked={tiposSeleccionados.includes(tipo.id)}
                              onChange={() => handleTipoToggle(tipo.id)}
                              className="checkbox checkbox-success checkbox-xs flex-shrink-0"
                              disabled={isSubmitting || !isSelected}
                            />
                            <span className="text-sm text-base-content">
                              {tipo.nombre}
                            </span>
                          </label>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            {errorMsg && recursosSeleccionados.length === 0 && (
              <label className="label">
                <span className="label-text-alt text-error">{errorMsg}</span>
              </label>
            )}
            {errorMsg &&
              tiposSeleccionados.length === 0 &&
              recursosSeleccionados.length > 0 && (
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
                    pattern="^$|^\d{4}(IE|EE|ER)\d{4,5}$"
                    title="Debe tener el formato: 4 números + IE o EE o ER + 4 o 5 números (ej: 2015IE5678)"
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
              maxLength={400}
            />
            <label className="label">
              <span className="label-text-alt text-base-content/60">
                Máximo 400 caracteres
              </span>
            </label>
          </div>

          {/* Error general */}
          {errorMsg &&
            recursosSeleccionados.length > 0 &&
            tiposSeleccionados.length > 0 &&
            quejosoSeleccionado.length > 0 && (
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

      <QuejosoSelectorModal
        isOpen={showQuejosoModal}
        title="Quejosos"
        quejosoList={quejosoList}
        selectedIds={quejosoSeleccionado}
        onSelectionChange={setQuejosoSeleccionado}
        onCreateQuejoso={handleCreateQuejoso}
        setToast={setToast}
        onClose={() => setShowQuejosoModal(false)}
        isDisabled={isSubmitting}
      />
    </div>
  );
}
