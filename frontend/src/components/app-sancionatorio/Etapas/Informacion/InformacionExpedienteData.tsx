import React, { useState, useRef, useEffect } from "react";
import { apiCall, API_CONFIG } from "../../../../utils/api";
import type { ExpedienteDetalle } from "../../../../types/sancionatorioApp";
import type { Municipio, ModeloGenerico } from "../../../../types/common";
import CustomSelect from "../../../Common/Form/CustomSelect";

const ETAPA_LABELS: Record<string, string> = {
  "INDAGACION PRELIMINAR": "Indagación Preliminar",
  "DETALLE MEDIDA PREVENTIVA": "Medida Preventiva",
  "INICIO PROCESO SANCIONATORIO": "Inicio Proceso Sancionatorio",
  "CESACION": "Cesacion",
  "FORMULACION DE CARGOS": "Formulacion de Cargos",
  "APERTURA ETAPA PROBATORIA": "Apertura Etapa Probatoria",
  "CIERRE ETAPA PROBATORIA": "Cierre Etapa Probatoria",
  "DECISION DE FONDO": "Decisión de Fondo",
  "RECURSO": "Probatoria del Recurso",
  "EJECUCION DE LA SANCION": "Ejecución Sanción",
};

const formatEtapa = (etapa?: string | null) =>
  etapa ? ETAPA_LABELS[etapa.toUpperCase()] || etapa : etapa;

interface Props {
  expediente: ExpedienteDetalle;
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  onUpdate?: (expediente: ExpedienteDetalle) => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
}

export default function InformacionExpedienteData({
  expediente,
  municipioList,
  recursoAfectadoList,
  onUpdate,
  setToast,
  isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [recursosSeleccionados, setRecursosSeleccionados] = useState<number[]>(
    expediente.recurso_afectado || [],
  );
  const [veredaList, setVeredaList] = useState<ModeloGenerico[]>([]);
  const [municipioId, setMunicipioId] = useState(expediente.municipio?.id || 0);
  const [veredaId, setVeredaId] = useState(expediente.vereda?.id || 0);
  const formRef = useRef<HTMLFormElement | null>(null);

  useEffect(() => {
    const town = municipioList.find((t) =>
      t.veredas.some((s) => s.id === expediente.vereda?.id),
    );
    setVeredaList(town?.veredas || []);
  }, [expediente, municipioList]);

  const handleResourceToggle = (id: number) => {
    setRecursosSeleccionados((prev) =>
      prev.includes(id) ? prev.filter((r) => r !== id) : [...prev, id],
    );
  };

  const toggleChangeTown = (townId: number) => {
    setMunicipioId(townId);
    setVeredaId(0);
    const town = municipioList.find((t) => t.id === townId);
    setVeredaList(town?.veredas || []);
  };

  const validateForm = () => {
    if (!municipioId) {
      setToast({ id: Date.now(), message: "Debe seleccionar un municipio", type: "error" });
      return false;
    }
    if (!veredaId) {
      setToast({ id: Date.now(), message: "Debe seleccionar una vereda", type: "error" });
      return false;
    }
    if (recursosSeleccionados.length === 0) {
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

    const resourcesChanged =
      JSON.stringify([...recursosSeleccionados].sort()) !==
      JSON.stringify([...(expediente.recurso_afectado || [])].sort());

    return (
      newRadicado !== expediente.radicado ||
      newNombre !== expediente.expediente ||
      newMotivo !== (expediente.motivo_afectacion || "") ||
      newDireccion !== expediente.direccion ||
      veredaId !== (expediente.vereda?.id || 0) ||
      municipioId !== expediente.municipio.id ||
      resourcesChanged
    );
  };

  const updateExpediente = async (expediente: ExpedienteDetalle): Promise<boolean> => {
    try {
      const updatePayload = {
        radicado: expediente.radicado,
        expediente: expediente.expediente,
        recurso: expediente.recurso_afectado || [],
        motivo: expediente.motivo_afectacion || "",
        vereda: expediente.vereda?.id || 0,
        direccion: expediente.direccion,
      };

      const response = await apiCall(
        API_CONFIG.ENDPOINTS.FILE_BASIC_DATA(expediente.id),
        {
          method: "PUT",
          body: JSON.stringify(updatePayload),
        },
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
        return false;
      }
    } catch (networkError) {
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

      const selectedMunicipio = municipioList.find((t) => t.id === municipioId);
      const selectedVereda = veredaList.find((s) => s.id === veredaId);

      const updatedExpediente: ExpedienteDetalle = {
        ...expediente,
        radicado: (formData.get("radicado") as string).trim(),
        expediente: (formData.get("nombre") as string).trim(),
        recurso_afectado: recursosSeleccionados,
        motivo_afectacion: (formData.get("motivo") as string).trim(),
        direccion: (formData.get("direccion") as string).trim(),
        vereda: {
          id: veredaId,
          nombre: selectedVereda?.nombre || "",
        },
        municipio: {
          id: municipioId,
          nombre: selectedMunicipio?.nombre || expediente.municipio.nombre,
        },
      };

      const updateSuccess = await updateExpediente(updatedExpediente);

      if (updateSuccess) {
        // Esperar un momento para que el servidor procese
        await new Promise((resolve) => setTimeout(resolve, 300));

        // Notificar al padre que se actualizó el expediente
        // El padre (FileDetail) se encargará de refrescar desde el servidor
        if (onUpdate) {
          await onUpdate(updatedExpediente);
        }

        // Actualizar el estado local de recursos seleccionados
        setRecursosSeleccionados(updatedExpediente.recurso_afectado || []);
        setShowForm(false);
      }
    } catch (error) {

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
    setRecursosSeleccionados(expediente.recurso_afectado || []);
    setMunicipioId(expediente.municipio?.id || 0);
    setVeredaId(expediente.vereda?.id || 0);
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
    <div className="card bg-base-100 shadow border border-base-300">
      <div className="card-body p-0">
        {/* Header */}
        <div className="px-5 py-4 border-b border-base-200 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-success/10 rounded-lg flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div>
              <p className="text-[10px] font-semibold text-base-content/50 uppercase tracking-wider">Expediente</p>
              <h2 className="text-base font-bold text-base-content">Datos del Expediente</h2>
            </div>
          </div>
          {!showForm && isEditable && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-success hover:bg-success/10"
              onClick={() => {
                setMunicipioId(expediente.municipio?.id || 0);
                setVeredaId(expediente.vereda?.id || 0);
                setShowForm(true);
              }}
              disabled={isLoading}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              Editar
            </button>
          )}
        </div>
        <div className="p-5">

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
                  <p className="text-sm font-semibold">{expediente.radicado}</p>
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
                  <p className="text-sm">{expediente.expediente}</p>
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
                    {expediente.vereda?.nombre || "No definido"}, {expediente.municipio.nombre}
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
                    {expediente.recurso_afectado && expediente.recurso_afectado.length > 0 ? (
                      expediente.recurso_afectado
                        .map(
                          (id) =>
                            recursoAfectadoList.find((recurso) => recurso.id === id)
                              ?.nombre,
                        )
                        .filter((nombre) => nombre)
                        .map((nombre, index) => (
                          <span
                            key={index}
                            className="badge badge-success text-white badge-sm"
                          >
                            {nombre}
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
                  <p className="text-sm">{formatDate(expediente.fecha_creacion)}</p>
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
                  {expediente.ultima_etapa ? (
                    <p className="text-sm font-medium text-success">
                      {formatEtapa(expediente.ultima_etapa)}
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
                  <p className="text-sm">{expediente.direccion}</p>
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
                    {expediente.motivo_afectacion || "Sin motivo especificado"}
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
                  defaultValue={expediente.radicado}
                  className="input input-bordered w-full"
                  required
                  disabled={isLoading}
                  pattern="^\d{4}(IE|EE|ER)\d{4,5}$"
                  title="Debe tener el formato: 4 números + IE o EE o ER + 4 o 5 números (ej: 2015IE5678)"
                />
              </div>

              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Expediente</span>
                </label>
                <input
                  type="text"
                  name="nombre"
                  defaultValue={expediente.expediente}
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
                <CustomSelect
                  value={municipioId}
                  onChange={toggleChangeTown}
                  placeholder="Seleccione un municipio"
                  disabled={isLoading}
                  options={municipioList.map((m) => ({ value: m.id, label: m.nombre }))}
                />
              </div>

              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Vereda</span>
                </label>
                <CustomSelect
                  value={veredaId}
                  onChange={setVeredaId}
                  placeholder="Seleccione una vereda"
                  disabled={isLoading}
                  options={veredaList.map((v) => ({ value: v.id, label: v.nombre }))}
                />
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
                  {recursoAfectadoList.map((r) => (
                    <label
                      key={r.id}
                      className="flex items-center gap-3 p-3 bg-base-100 rounded-lg border border-base-300 hover:border-success/50 cursor-pointer transition-colors"
                    >
                      <input
                        type="checkbox"
                        value={r.id}
                        checked={recursosSeleccionados.includes(r.id)}
                        onChange={() => handleResourceToggle(r.id)}
                        className="checkbox checkbox-success checkbox-sm"
                        disabled={isLoading}
                      />
                      <span className="text-sm font-medium">{r.nombre}</span>
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
                defaultValue={expediente.direccion}
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
                defaultValue={expediente.motivo_afectacion || ""}
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
    </div>
  );
}
