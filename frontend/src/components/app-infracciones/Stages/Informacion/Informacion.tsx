import { useEffect, useMemo, useState, type FormEvent } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import type { ExpedienteDetalle } from "../../../../types/infraccionApp";
import type { Municipio, ModeloGenerico } from "../../../../types/common";

type ExpedienteDetalleExt = ExpedienteDetalle & {
  radicados_asociados?: string[];
};

interface Props {
  expediente: ExpedienteDetalle;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  quejosoList: ModeloGenerico[];
  causaList: ModeloGenerico[];
  onUpdate?: (expediente: ExpedienteDetalle) => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
}

const RADICADO_REGEX = /^\d{4}(IE|EE|ER)\d{4}$/;

export default function BasicDataFile({
  expediente,
  municipioList,
  recursoAfectadoList,
  quejosoList,
  causaList,
  onUpdate,
  setToast,
  isEditable = true,
}: Props) {
  const expedienteExt = expediente as ExpedienteDetalleExt;

  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const [radicado, setRadicado] = useState(expediente.radicado || "");
  const [fechaRadicado, setFechaRadicado] = useState(
    expediente.fecha_radicado || "",
  );
  const [municipioId, setMunicipioId] = useState(expediente.municipio?.id || 0);
  const [veredaId, setVeredaId] = useState(expediente.vereda?.id || 0);
  const [direccion, setDireccion] = useState(expediente.direccion || "");
  const [causaId, setCausaId] = useState(expediente.causa?.id || 0);
  const [descripcion, setDescripcion] = useState(expediente.descripcion || "");
  const [recursosIds, setRecursosIds] = useState<number[]>(
    (expediente.recurso_afectado || []).map((r) => r.id),
  );
  const [quejososIds, setQuejososIds] = useState<number[]>(
    (expediente.quejosos || []).map((q) => q.id),
  );
  const [radicadosAsociados, setRadicadosAsociados] = useState<string[]>(
    expedienteExt.radicados_asociados &&
      expedienteExt.radicados_asociados.length > 0
      ? expedienteExt.radicados_asociados
      : [""],
  );

  useEffect(() => {
    const next = expediente as ExpedienteDetalleExt;
    setRadicado(expediente.radicado || "");
    setFechaRadicado(expediente.fecha_radicado || "");
    setMunicipioId(expediente.municipio?.id || 0);
    setVeredaId(expediente.vereda?.id || 0);
    setDireccion(expediente.direccion || "");
    setCausaId(expediente.causa?.id || 0);
    setDescripcion(expediente.descripcion || "");
    setRecursosIds((expediente.recurso_afectado || []).map((r) => r.id));
    setQuejososIds((expediente.quejosos || []).map((q) => q.id));
    setRadicadosAsociados(
      next.radicados_asociados && next.radicados_asociados.length > 0
        ? next.radicados_asociados
        : [""],
    );
  }, [expediente]);

  const veredaList = useMemo(() => {
    const municipio = municipioList.find((m) => m.id === municipioId);
    return municipio?.veredas || [];
  }, [municipioList, municipioId]);

  const formatDate = (dateString: string) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    return date.toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  };

  const handleResourceToggle = (id: number) => {
    setRecursosIds((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id],
    );
  };

  const handleQuejosoToggle = (id: number) => {
    setQuejososIds((prev) =>
      prev.includes(id) ? prev.filter((q) => q !== id) : [...prev, id],
    );
  };

  const handleAddRadicado = () => {
    setRadicadosAsociados((prev) => [...prev, ""]);
  };

  const handleRemoveRadicado = (index: number) => {
    setRadicadosAsociados((prev) =>
      prev.length === 1 ? [""] : prev.filter((_, i) => i !== index),
    );
  };

  const handleChangeRadicadoAsociado = (index: number, value: string) => {
    setRadicadosAsociados((prev) =>
      prev.map((item, i) => (i === index ? value.toUpperCase() : item)),
    );
  };

  const resetForm = () => {
    const next = expediente as ExpedienteDetalleExt;
    setRadicado(expediente.radicado || "");
    setFechaRadicado(expediente.fecha_radicado || "");
    setMunicipioId(expediente.municipio?.id || 0);
    setVeredaId(expediente.vereda?.id || 0);
    setDireccion(expediente.direccion || "");
    setCausaId(expediente.causa?.id || 0);
    setDescripcion(expediente.descripcion || "");
    setRecursosIds((expediente.recurso_afectado || []).map((r) => r.id));
    setQuejososIds((expediente.quejosos || []).map((q) => q.id));
    setRadicadosAsociados(
      next.radicados_asociados && next.radicados_asociados.length > 0
        ? next.radicados_asociados
        : [""],
    );
  };

  const validateForm = (): boolean => {
    if (!RADICADO_REGEX.test(radicado.trim())) {
      setToast({
        id: Date.now(),
        message: "El radicado no cumple el formato requerido",
        type: "error",
      });
      return false;
    }

    if (quejososIds.length === 0) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar al menos un quejoso",
        type: "error",
      });
      return false;
    }

    if (recursosIds.length === 0) {
      setToast({
        id: Date.now(),
        message: "Debe seleccionar al menos un recurso afectado",
        type: "error",
      });
      return false;
    }

    for (const item of radicadosAsociados) {
      const value = item.trim();
      if (!value) continue;
      if (!RADICADO_REGEX.test(value)) {
        setToast({
          id: Date.now(),
          message: "Todos los radicados asociados deben tener formato valido",
          type: "error",
        });
        return false;
      }
    }

    return true;
  };

  const buildUpdatedExpediente = (): ExpedienteDetalleExt => {
    const selectedMunicipio = municipioList.find((m) => m.id === municipioId);
    const selectedVereda = veredaList.find((v) => v.id === veredaId);
    const selectedCausa = causaList.find((c) => c.id === causaId);

    return {
      ...expediente,
      radicado: radicado.trim(),
      fecha_radicado: fechaRadicado,
      direccion: direccion.trim(),
      descripcion: descripcion.trim(),
      municipio: {
        id: municipioId,
        nombre: selectedMunicipio?.nombre || expediente.municipio.nombre,
      },
      vereda: {
        id: veredaId,
        nombre: selectedVereda?.nombre || expediente.vereda?.nombre || "",
      },
      causa: {
        id: causaId,
        nombre: selectedCausa?.nombre || expediente.causa?.nombre || "",
      },
      recurso_afectado: recursoAfectadoList.filter((r) =>
        recursosIds.includes(r.id),
      ),
      quejosos: quejosoList.filter((q) => quejososIds.includes(q.id)),
      radicados_asociados: radicadosAsociados
        .map((r) => r.trim())
        .filter((r) => r.length > 0),
    };
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();

    if (!validateForm()) return;

    const updated = buildUpdatedExpediente();

    const payload = {
      radicado: updated.radicado,
      fecha_radicado: updated.fecha_radicado,
      vereda_id: updated.vereda.id,
      direccion: updated.direccion,
      descripcion: updated.descripcion,
      causa_id: updated.causa.id,
      quejosos_ids: quejososIds,
      recursos_ids: recursosIds,
      radicados_asociados: updated.radicados_asociados || [],

      // Compatibilidad temporal con backend legacy.
      vereda: updated.vereda.id,
      causa: updated.causa.id,
      quejosos: quejososIds,
      recurso: recursosIds,
    };

    setIsLoading(true);
    try {
      const response = await apiCall(
        API_CONFIG.ENDPOINTS.INFRACTION_BASIC_DATA(expediente.id),
        {
          method: "PUT",
          body: JSON.stringify(payload),
        },
      );

      if (!response.ok) {
        setToast({
          id: Date.now(),
          message: response.detail || "No se pudo actualizar el expediente",
          type: "error",
        });
        return;
      }

      setToast({
        id: Date.now(),
        message: "Expediente actualizado exitosamente",
        type: "success",
      });

      if (onUpdate) onUpdate(updated);
      setShowForm(false);
    } catch {
      setToast({
        id: Date.now(),
        message: "Error de conexion al actualizar el expediente",
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    resetForm();
    setShowForm(false);
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
                Informacion basica del caso
              </p>
            </div>
          </div>
          {!showForm && isEditable && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-success hover:bg-success/10"
              onClick={() => setShowForm(true)}
              disabled={isLoading}
            >
              Editar
            </button>
          )}
        </div>

        {!showForm && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-3">
              <p>
                <span className="font-semibold">Radicado:</span>{" "}
                {expediente.radicado}
              </p>
              <p>
                <span className="font-semibold">Fecha radicado:</span>{" "}
                {formatDate(expediente.fecha_radicado)}
              </p>
              <p>
                <span className="font-semibold">Quejoso:</span>{" "}
                {(expediente.quejosos || []).map((q) => q.nombre).join(", ") ||
                  "Sin quejosos"}
              </p>
              <p>
                <span className="font-semibold">Municipio:</span>{" "}
                {expediente.municipio?.nombre || "Sin municipio"}
              </p>
              <p>
                <span className="font-semibold">Vereda:</span>{" "}
                {expediente.vereda?.nombre || "Sin vereda"}
              </p>
              <p>
                <span className="font-semibold">Direccion:</span>{" "}
                {expediente.direccion || "Sin direccion"}
              </p>
            </div>
            <div className="space-y-3">
              <p>
                <span className="font-semibold">Causa:</span>{" "}
                {expediente.causa?.nombre || "Sin causa"}
              </p>
              <p>
                <span className="font-semibold">Recursos afectados:</span>{" "}
                {(expediente.recurso_afectado || [])
                  .map((r) => r.nombre)
                  .join(", ") || "Sin recursos"}
              </p>
              <p>
                <span className="font-semibold">Radicados asociados:</span>{" "}
                {(expedienteExt.radicados_asociados || []).join(", ") ||
                  "Sin radicados asociados"}
              </p>
              <p>
                <span className="font-semibold">Descripcion:</span>{" "}
                {expediente.descripcion || "Sin descripcion"}
              </p>
            </div>
          </div>
        )}

        {showForm && isEditable && (
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">Radicado *</span>
              </label>
              <input
                className="input input-bordered"
                value={radicado}
                onChange={(e) => setRadicado(e.target.value.toUpperCase())}
                maxLength={15}
                required
                pattern="^\d{4}(IE|EE|ER)\d{4}$"
                title="Debe tener el formato: 4 numeros + IE o EE o ER + 4 numeros (ej: 2015IE5678)"
                disabled={isLoading}
              />
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">Fecha radicado *</span>
              </label>
              <input
                type="date"
                className="input input-bordered"
                value={fechaRadicado}
                onChange={(e) => setFechaRadicado(e.target.value)}
                required
                disabled={isLoading}
              />
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">Quejoso *</span>
              </label>
              <div className="bg-base-200 rounded-lg p-4 border border-base-300">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {quejosoList.map((q) => (
                    <label
                      key={q.id}
                      className="flex items-center gap-3 p-3 bg-base-100 rounded-lg border border-base-300 hover:border-success cursor-pointer transition-colors"
                    >
                      <input
                        type="checkbox"
                        className="checkbox checkbox-success checkbox-sm"
                        checked={quejososIds.includes(q.id)}
                        onChange={() => handleQuejosoToggle(q.id)}
                        disabled={isLoading}
                      />
                      <span className="text-sm font-medium text-base-content">
                        {q.nombre}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">Municipio *</span>
              </label>
              <select
                className="select select-bordered"
                value={municipioId || ""}
                onChange={(e) => {
                  setMunicipioId(Number(e.target.value));
                  setVeredaId(0);
                }}
                required
                disabled={isLoading}
              >
                <option value="" disabled>
                  Seleccione un municipio
                </option>
                {municipioList.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">Vereda *</span>
              </label>
              <select
                className="select select-bordered"
                value={veredaId || ""}
                onChange={(e) => setVeredaId(Number(e.target.value))}
                required
                disabled={isLoading || veredaList.length === 0}
              >
                <option value="" disabled>
                  {veredaList.length === 0
                    ? "Seleccione primero un municipio"
                    : "Seleccione una vereda"}
                </option>
                {veredaList.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">Direccion *</span>
              </label>
              <input
                className="input input-bordered"
                value={direccion}
                onChange={(e) => setDireccion(e.target.value)}
                maxLength={100}
                required
                disabled={isLoading}
              />
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">Causa *</span>
              </label>
              <select
                className="select select-bordered"
                value={causaId || ""}
                onChange={(e) => setCausaId(Number(e.target.value))}
                required
                disabled={isLoading}
              >
                <option value="" disabled>
                  Seleccione una causa
                </option>
                {causaList.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Recursos afectados *
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
                        className="checkbox checkbox-success checkbox-sm"
                        checked={recursosIds.includes(r.id)}
                        onChange={() => handleResourceToggle(r.id)}
                        disabled={isLoading}
                      />
                      <span className="text-sm font-medium text-base-content">
                        {r.nombre}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Radicados asociados
                </span>
              </label>
              <div className="space-y-2">
                {radicadosAsociados.map((item, index) => (
                  <div key={index} className="flex gap-2">
                    <input
                      className="input input-bordered w-full"
                      value={item}
                      onChange={(e) =>
                        handleChangeRadicadoAsociado(index, e.target.value)
                      }
                      maxLength={15}
                      pattern="^$|^\d{4}(IE|EE|ER)\d{4}$"
                      title="Debe tener el formato: 4 numeros + IE o EE o ER + 4 numeros (ej: 2015IE5678)"
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      className="btn btn-outline btn-error"
                      onClick={() => handleRemoveRadicado(index)}
                      disabled={isLoading}
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
                  onClick={handleAddRadicado}
                  disabled={isLoading}
                >
                  + Agregar radicado
                </button>
              </div>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">Descripcion *</span>
              </label>
              <textarea
                className="textarea textarea-bordered h-24 resize-none"
                value={descripcion}
                onChange={(e) => setDescripcion(e.target.value)}
                maxLength={300}
                required
                disabled={isLoading}
              />
              <label className="label">
                <span className="label-text-alt text-base-content/60">
                  Maximo 300 caracteres
                </span>
              </label>
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
                {isLoading ? "Guardando..." : "Guardar Cambios"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
