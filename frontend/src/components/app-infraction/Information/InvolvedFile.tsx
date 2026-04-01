import React, { useState, useCallback, useEffect, useRef } from "react";
import type { File, Involved } from "../../../types/index";
import { apiCall, API_CONFIG } from "../../../utils/api";
import ConfirmDeleteInvolvedModal from "./ConfirmDeleteInvolvedModal";

interface Props {
  file: File;
  onFileUpdate?: (updatedFile: File) => void;
  setToast: (toast: {
    id: number;
    message: string;
    type: "success" | "error";
  }) => void;
  isEditable?: boolean;
}

// Actualizada la interfaz para incluir el DV
interface InvolucradoForm {
  numero_documento: string;
  digito_verificacion: string;
  tipo_documento: string;
  nombre: string;
  celular: string;
  correo: string;
}

const initialFormData: InvolucradoForm = {
  numero_documento: "",
  digito_verificacion: "",
  tipo_documento: "CC",
  nombre: "",
  celular: "",
  correo: "",
};

const capitalizeName = (name: string): string => {
  return name
    .trim()
    .toLowerCase()
    .split(" ")
    .filter((word) => word.length > 0)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
};

export default function InvolvedFile({
  file,
  onFileUpdate,
  setToast,
  isEditable = true,
}: Props) {
  const [showForm, setShowForm] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [existingInvolucrado, setExistingInvolucrado] = useState<any>(null);
  const [formData, setFormData] = useState<InvolucradoForm>(initialFormData);
  const [involvedList, setInvolvedList] = useState<Involved[]>(
    file.involucrados || [],
  );

  useEffect(() => {
    setInvolvedList(file.involucrados || []);
  }, [file.involucrados]);

  const searchInvolucrado = useCallback(
    async (numeroDocumento: string, tipoDocumento: string, dv?: string) => {
      if (
        !numeroDocumento.trim() ||
        !tipoDocumento.trim() ||
        numeroDocumento.length < 7
      ) {
        return;
      }

      // Si es NIT y no hay DV, no buscar aún
      if (tipoDocumento === "NIT" && !dv?.trim()) {
        return;
      }

      try {
        setIsLoading(true);

        // Usar endpoint centralizado de app-involved con parámetros correctos
        const endpoint = API_CONFIG.ENDPOINTS.INVOLVED_SEARCH(
          tipoDocumento,
          numeroDocumento,
          dv,
        );

        const data = await apiCall(endpoint);

        if (data.ok && data.data) {
          const involucrado = data.data;

          setFormData({
            numero_documento: involucrado.numero_documento.toString(),
            digito_verificacion: involucrado.digito_verificacion || "",
            tipo_documento: involucrado.tipo_documento,
            nombre: involucrado.nombre,
            celular: involucrado.celular.toString(),
            correo: involucrado.correo,
          });

          setExistingInvolucrado(involucrado);
        }
      } catch (error: any) {
        if (error.message.includes("404")) {
          // Involucrado no encontrado - habilitar creación
          setExistingInvolucrado(null);
        } else if (
          error.message.includes("503") ||
          error.message.includes("Service Unavailable")
        ) {
          setToast({
            id: Date.now(),
            message:
              "Servicio de involucrados no disponible. Intente más tarde.",
            type: "error",
          });
        } else {
          /* console.error("Error buscando involucrado:", error); */
        }
      } finally {
        setIsLoading(false);
      }
    },
    [setToast],
  );

  const createInvolucrado = async () => {
    const payload = {
      numero_documento: formData.numero_documento.trim(),
      // Solo enviamos DV si es NIT
      digito_verificacion:
        formData.tipo_documento === "NIT" ? formData.digito_verificacion : null,
      tipo_documento: formData.tipo_documento,
      nombre: capitalizeName(formData.nombre),
      celular: formData.celular.trim(),
      correo: formData.correo.trim().toLowerCase(),
    };

    return await apiCall(API_CONFIG.ENDPOINTS.INVOLVED_CREATE, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  };

  const linkInvolucradoToExpediente = async (
    numeroDocumento: string,
    tipoDocumento: string,
    dv?: string,
  ) => {
    const payload = {
      expediente_radicado: file.radicado,
      involucrado_numero_documento: numeroDocumento,
      involucrado_tipo_documento: tipoDocumento,
      involucrado_digito_verificacion:
        tipoDocumento === "NIT" ? dv || null : null,
    };

    return await apiCall(API_CONFIG.ENDPOINTS.INVOLVED_EXPEDIENTE_LINK, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      let involucradoData;

      // Paso 1: Crear o usar involucrado existente
      if (!existingInvolucrado) {
        const createResponse = await createInvolucrado();

        // Verificar que la creación fue exitosa
        if (!createResponse || !createResponse.ok) {
          throw new Error("Error al crear el involucrado");
        }

        involucradoData = {
          id: createResponse.data.id,
          numero_documento: parseInt(formData.numero_documento.trim()),
          // Guardamos DV localmente si es NIT
          digito_verificacion:
            formData.tipo_documento === "NIT"
              ? formData.digito_verificacion
              : null,
          tipo_documento: formData.tipo_documento,
          nombre: capitalizeName(formData.nombre),
          celular: parseInt(formData.celular.trim()),
          correo: formData.correo.trim().toLowerCase(),
        };
      } else {
        involucradoData = {
          ...existingInvolucrado,
          numero_documento: parseInt(existingInvolucrado.numero_documento),
          celular: parseInt(existingInvolucrado.celular),
        };
      }

      // Verificar si ya existe en la lista local
      const yaExisteEnLista = involvedList.some(
        (inv) =>
          inv.numero_documento == involucradoData.numero_documento &&
          inv.tipo_documento === involucradoData.tipo_documento,
      );

      if (yaExisteEnLista) {
        setToast({
          id: Date.now(),
          message: "Este involucrado ya está vinculado a este expediente",
          type: "error",
        });
        setIsLoading(false);
        return;
      }

      // Paso 2: Vincular al expediente
      const linkResponse = await linkInvolucradoToExpediente(
        formData.numero_documento.trim(),
        formData.tipo_documento,
        formData.digito_verificacion,
      );

      // Verificar que la vinculación fue exitosa
      if (!linkResponse || !linkResponse.ok) {
        throw new Error(
          linkResponse?.detail || "Error al vincular el involucrado",
        );
      }

      // Solo actualizar el estado local si TODO fue exitoso
      const updatedInvolvedList = [...involvedList, involucradoData];
      const updatedFile = { ...file, involucrados: updatedInvolvedList };

      setInvolvedList(updatedInvolvedList);
      if (onFileUpdate) {
        onFileUpdate(updatedFile);
      }

      resetForm();
      setToast({
        id: Date.now(),
        message: "Involucrado vinculado exitosamente",
        type: "success",
      });
    } catch (error: any) {
      /* console.error("Error:", error); */

      let errorMessage = "Error desconocido";
      if (error.message.includes("400")) {
        if (error.message.includes("ya está vinculado")) {
          errorMessage = "Este involucrado ya está vinculado a este expediente";
        } else if (error.message.includes("ya existe")) {
          errorMessage = "Ya existe un involucrado con ese documento";
        } else {
          errorMessage = "Solicitud inválida";
        }
      } else if (error.message.includes("404")) {
        errorMessage = "Expediente no encontrado";
      } else if (error.message.includes("500")) {
        errorMessage = "Error interno del servidor";
      } else {
        errorMessage = error.message;
      }

      setToast({ id: Date.now(), message: errorMessage, type: "error" });
    } finally {
      setIsLoading(false);
    }
  };

  const [userDelete, setUserDelete] = useState<Involved | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const handleConfirm = () => {
    confirmResolver.current?.(true);
    confirmResolver.current = null;
    setIsOpen(false);
  };

  const handleClose = () => {
    confirmResolver.current?.(false);
    confirmResolver.current = null;
    setIsOpen(false);
  };

  const confirmResolver = useRef<((value: boolean) => void) | null>(null);

  function confirmDeleteUser(user: Involved): Promise<boolean> {
    return new Promise((resolve) => {
      setUserDelete(user);
      setIsOpen(true);
      confirmResolver.current = resolve;
    });
  }

  const deleteInvolucrado = async (idx: number) => {
    const involucrado = involvedList[idx];
    const confirmed = await confirmDeleteUser(involucrado);

    if (!confirmed) return;

    try {
      setIsLoading(true);

      // Primero eliminar en el servidor
      const deleteResponse = await apiCall(
        API_CONFIG.ENDPOINTS.INVOLVED_EXPEDIENTE_UNLINK(involucrado.id),
        { method: "DELETE" },
      );

      // Verificar que la eliminación fue exitosa
      if (!deleteResponse || !deleteResponse.ok) {
        throw new Error(
          deleteResponse?.detail || "Error al desvincular el involucrado",
        );
      }

      // Solo actualizar el estado local si la eliminación fue exitosa
      const updatedInvolvedList = involvedList.filter((_, i) => i !== idx);
      const updatedFile = { ...file, involucrados: updatedInvolvedList };

      setInvolvedList(updatedInvolvedList);
      if (onFileUpdate) {
        onFileUpdate(updatedFile);
      }

      setToast({
        id: Date.now(),
        message: "Involucrado desvinculado exitosamente",
        type: "success",
      });
    } catch (error: any) {
      /* console.error("Error al eliminar:", error); */

      setToast({
        id: Date.now(),
        message: `Error al desvincular: ${error.message}`,
        type: "error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const resetForm = () => {
    setFormData(initialFormData);
    setExistingInvolucrado(null);
    setShowForm(false);
  };

  const handleDocumentChange = (value: string) => {
    const newValue = value.replace(/\D/g, "");
    setFormData({ ...formData, numero_documento: newValue });

    if (
      existingInvolucrado &&
      newValue !== existingInvolucrado.numero_documento.toString()
    ) {
      setExistingInvolucrado(null);
      setFormData({
        ...initialFormData,
        numero_documento: newValue,
        digito_verificacion: formData.digito_verificacion,
        tipo_documento: formData.tipo_documento,
      });
    }
  };

  const handleTipoDocumentoChange = (value: string) => {
    if (existingInvolucrado && value !== existingInvolucrado.tipo_documento) {
      setExistingInvolucrado(null);
      setFormData({
        ...initialFormData,
        tipo_documento: value,
        numero_documento: formData.numero_documento,
        digito_verificacion:
          value === "NIT" ? formData.digito_verificacion : "",
      });
    } else {
      setFormData({
        ...formData,
        tipo_documento: value,
        // Limpiar DV si cambia a algo que no es NIT
        digito_verificacion:
          value === "NIT" ? formData.digito_verificacion : "",
      });
    }
  };

  const handleDocumentBlur = () => {
    if (formData.numero_documento.length >= 7 && !existingInvolucrado) {
      // Si es NIT, también necesitamos el DV para buscar
      if (formData.tipo_documento === "NIT") {
        if (formData.digito_verificacion) {
          searchInvolucrado(
            formData.numero_documento,
            formData.tipo_documento,
            formData.digito_verificacion,
          );
        }
      } else {
        searchInvolucrado(formData.numero_documento, formData.tipo_documento);
      }
    }
  };

  const handleDVBlur = () => {
    // Buscar cuando se complete el DV (solo para NIT)
    if (
      formData.tipo_documento === "NIT" &&
      formData.numero_documento.length >= 7 &&
      formData.digito_verificacion &&
      !existingInvolucrado
    ) {
      searchInvolucrado(
        formData.numero_documento,
        formData.tipo_documento,
        formData.digito_verificacion,
      );
    }
  };

  const handleNameChange = (value: string) => {
    setFormData({ ...formData, nombre: value });
  };

  const getDocumentTypeColor = (type: string) => {
    const colors = {
      CC: "badge-info",
      NIT: "badge-success",
      CE: "badge-warning",
      PP: "badge-secondary",
    };
    return colors[type as keyof typeof colors] || "badge-ghost";
  };

  return (
    <div className="card bg-base-100 shadow-md border border-base-300">
      <div className="card-body">
        {isOpen && userDelete && (
          <ConfirmDeleteInvolvedModal
            user={userDelete}
            isOpen={isOpen}
            onClose={handleClose}
            onConfirm={handleConfirm}
          />
        )}

        {/* HEADER */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-warning/20 rounded-lg flex items-center justify-center">
              <svg
                className="w-5 h-5 text-warning"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8.8 4.354a4 4 0 1 0 0 8a4 4 0 1 0 0-8M15 23H3v-1a6 6 0 0 1 12 0v1zm0 0h6v-1a6 6 0 0 0-9-5.197m6-9a2.5 2.5 0 1 1-5 0a2.5 2.5 0 0 1 5 0z"
                />
              </svg>
            </div>
            <div>
              <h3 className="text-xl font-bold">Presuntos Infractores</h3>
              <p className="text-sm text-base-content/60">
                {involvedList.length} persona
                {involvedList.length !== 1 ? "s" : ""} vinculada
                {involvedList.length !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
          {!showForm && isEditable && (
            <button
              className="btn btn-ghost btn-sm gap-2 text-warning hover:bg-warning/10"
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
                  d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                />
              </svg>
              Agregar
            </button>
          )}
        </div>

        {/* LISTA DE INVOLUCRADOS */}
        {!showForm && (
          <div className="space-y-4">
            {involvedList.length > 0 ? (
              <div className="space-y-3">
                {involvedList.map((involucrado: Involved, idx: number) => (
                  <div
                    key={`${involucrado.tipo_documento}-${involucrado.numero_documento}-${idx}`}
                    className="flex items-center justify-between p-4 bg-base-200 rounded-lg border border-base-300 hover:border-warning/30 transition-colors"
                  >
                    <div className="flex items-center gap-4 flex-1">
                      {/* Avatar con iniciales */}
                      <div className="avatar placeholder">
                        <div className="w-12 h-12 rounded-full bg-warning text-white !grid !place-items-center overflow-hidden">
                          <span className="text-sm font-bold leading-none">
                            {involucrado.nombre
                              .split(" ")
                              .map((n) => n?.[0] ?? "")
                              .join("")
                              .substring(0, 2)
                              .toUpperCase()}
                          </span>
                        </div>
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <h4 className="font-semibold truncate">
                            {involucrado.nombre}
                          </h4>
                          <span
                            className={`badge badge-sm ${getDocumentTypeColor(
                              involucrado.tipo_documento,
                            )}`}
                          >
                            {involucrado.tipo_documento}
                          </span>
                        </div>

                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm text-base-content/70">
                          <div className="flex items-center gap-1">
                            <svg
                              className="w-4 h-4 text-base-content/50"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V4a2 2 0 114 0v2m-4 0a2 2 0 104 0m-4 0v2"
                              />
                            </svg>
                            <span className="font-mono">
                              {involucrado.numero_documento}
                              {/* Mostrar DV en la lista si existe */}
                              {involucrado.digito_verificacion
                                ? `-${involucrado.digito_verificacion}`
                                : ""}
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            <svg
                              className="w-4 h-4 text-base-content/50"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"
                              />
                            </svg>
                            <span>{involucrado.celular}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <svg
                              className="w-4 h-4 text-base-content/50"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207"
                              />
                            </svg>
                            <span className="truncate">
                              {involucrado.correo}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Botón eliminar - Solo visible si isEditable */}
                    {isEditable && (
                      <button
                        onClick={() => deleteInvolucrado(idx)}
                        disabled={isLoading}
                        className="btn btn-ghost btn-sm text-error hover:bg-error/10 ml-3"
                        title="Desvincular del expediente"
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
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-base-200 rounded-lg border border-base-300 p-6">
                <div className="text-center py-8">
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
                        d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
                      />
                    </svg>
                  </div>
                  <h3 className="text-base font-medium text-base-content/70 mb-1">
                    Sin involucrados
                  </h3>
                  <p className="text-sm text-base-content/60">
                    No hay personas vinculadas a este expediente
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {/* FORMULARIO - Solo visible si isEditable */}
        {showForm && isEditable && (
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Alerta de involucrado encontrado */}
            {existingInvolucrado && (
              <div className="alert alert-success text-white">
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
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <span className="text-sm ">
                  Involucrado encontrado en el sistema - Solo se vinculará al
                  expediente
                </span>
              </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Tipo de documento */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">
                    Tipo de documento *
                  </span>
                </label>
                <select
                  value={formData.tipo_documento}
                  onChange={(e) => handleTipoDocumentoChange(e.target.value)}
                  className="select select-bordered w-full"
                  required
                  disabled={isLoading}
                >
                  <option value="CC">Cédula de Ciudadanía</option>
                  <option value="NIT">NIT</option>
                  <option value="CE">Cédula de Extranjería</option>
                  <option value="PP">Pasaporte</option>
                </select>
              </div>

              {/* Número de documento Y DIGITO DE VERIFICACIÓN */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">
                    Número de documento *
                    {isLoading && (
                      <span className="loading loading-spinner loading-xs ml-2"></span>
                    )}
                  </span>
                </label>

                {/* Contenedor Flex para alinear documento y DV */}
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={formData.numero_documento}
                    onChange={(e) => handleDocumentChange(e.target.value)}
                    onBlur={handleDocumentBlur}
                    className="input input-bordered flex-1 font-mono"
                    required
                    disabled={isLoading}
                    placeholder="Ej: 1234567890"
                    minLength={7}
                    maxLength={15}
                  />

                  {/* INPUT DE DV: Solo visible si es NIT */}
                  {formData.tipo_documento === "NIT" && (
                    <div className="tooltip" data-tip="Dígito de Verificación">
                      <input
                        type="text"
                        value={formData.digito_verificacion}
                        onChange={(e) => {
                          // Solo números y máximo 2 caracteres
                          const val = e.target.value
                            .replace(/\D/g, "")
                            .slice(0, 2);
                          setFormData({
                            ...formData,
                            digito_verificacion: val,
                          });
                        }}
                        onBlur={handleDVBlur}
                        className="input input-bordered w-16 text-center font-mono"
                        required
                        disabled={isLoading}
                        placeholder="DV"
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Nombre */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">
                    Nombre completo *
                  </span>
                </label>
                <input
                  type="text"
                  value={formData.nombre}
                  onChange={(e) => handleNameChange(e.target.value)}
                  className={`input input-bordered w-full ${existingInvolucrado ? "input-disabled" : ""
                    }`}
                  required
                  disabled={isLoading || !!existingInvolucrado}
                  placeholder="Nombre completo"
                  maxLength={100}
                />
              </div>

              {/* Celular */}
              <div className="form-control">
                <label className="label">
                  <span className="label-text font-medium">Celular *</span>
                </label>
                <input
                  type="text"
                  value={formData.celular}
                  onChange={(e) => {
                    const value = e.target.value.replace(/\D/g, "");
                    setFormData({ ...formData, celular: value });
                  }}
                  className={`input input-bordered w-full font-mono ${existingInvolucrado ? "input-disabled" : ""
                    }`}
                  required
                  disabled={isLoading || !!existingInvolucrado}
                  placeholder="Ej: 3001234567"
                  minLength={10}
                  maxLength={15}
                />
              </div>
            </div>

            {/* Correo */}
            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Correo electrónico *
                </span>
              </label>
              <input
                type="email"
                value={formData.correo}
                onChange={(e) =>
                  setFormData({ ...formData, correo: e.target.value })
                }
                className={`input input-bordered w-full ${existingInvolucrado ? "input-disabled" : ""
                  }`}
                required
                disabled={isLoading || !!existingInvolucrado}
                placeholder="ejemplo@correo.com"
                maxLength={100}
              />
            </div>

            {/* Botones */}
            <div className="flex gap-3 justify-end pt-4 border-t border-base-300">
              <button
                type="button"
                onClick={resetForm}
                className="btn btn-outline"
                disabled={isLoading}
              >
                Cancelar
              </button>
              <button
                type="submit"
                className="btn btn-warning text-white gap-2"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <span className="loading loading-spinner loading-sm"></span>
                    {existingInvolucrado
                      ? "Vinculando..."
                      : "Creando y vinculando..."}
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
                        d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                      />
                    </svg>
                    {existingInvolucrado
                      ? "Vincular al Expediente"
                      : "Crear y Vincular"}
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
