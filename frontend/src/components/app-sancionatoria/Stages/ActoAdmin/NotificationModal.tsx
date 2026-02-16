import { useState, useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import type {
  Involved,
  TipoNotificacion,
  InvolucradoNotificacion,
} from "../../../../types";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  editingNotificacion: InvolucradoNotificacion | null;
  involucrados: Involved[];
  yaNotificados: number[];
  tiposNotificacion: TipoNotificacion[];
  onSave: (formData: FormData) => Promise<{ ok: boolean; error?: string }>;
  isEditable?: boolean;
  notificacionesExistentes?: InvolucradoNotificacion[];
};

export default function NotificacionModal({
  isOpen,
  onClose,
  editingNotificacion,
  involucrados,
  yaNotificados,
  tiposNotificacion,
  onSave,
}: Props) {
  const [notificacionForm, setNotificacionForm] = useState({
    involucrado_id: 0,
    numerado: "",
    fecha_numerado: "",
    fecha_envio_citacion: "",
    fecha_constancia_citacion: "",
    notificacion_exitosa: false,
    tipo_notificacion_id: 0,
  });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFileCitacion, setSelectedFileCitacion] = useState<File | null>(
    null,
  );
  const [theme, setTheme] = useState<string>("emerald");
  const [errors, setErrors] = useState({
    involucrado_id: "",
    numerado: "",
    fecha_numerado: "",
    fecha_envio_citacion: "",
    fecha_constancia_citacion: "",
    tipo_notificacion_id: "",
    file: "",
    file_citacion: "",
    general: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const fileCitacionInputRef = useRef<HTMLInputElement>(null);

  const isEditing = !!editingNotificacion;

  // Detectar tema cada vez que se abre el modal
  useEffect(() => {
    if (isOpen) {
      const currentTheme =
        document.querySelector("[data-theme]")?.getAttribute("data-theme") ||
        "emerald";
      setTheme(currentTheme);
    }
  }, [isOpen]);

  // Reset form cuando se abre el modal
  useEffect(() => {
    if (isOpen) {
      setErrors({
        involucrado_id: "",
        numerado: "",
        fecha_numerado: "",
        fecha_envio_citacion: "",
        fecha_constancia_citacion: "",
        tipo_notificacion_id: "",
        file: "",
        file_citacion: "",
        general: "",
      });

      if (editingNotificacion) {
        setNotificacionForm({
          involucrado_id: editingNotificacion.involucrado_id,
          numerado: String(editingNotificacion.numerado || "").padStart(4, "0"),
          fecha_numerado: editingNotificacion.fecha_numerado,
          fecha_envio_citacion: editingNotificacion.fecha_envio_citacion,
          fecha_constancia_citacion:
            editingNotificacion.fecha_constancia_citacion || "",
          notificacion_exitosa: editingNotificacion.notificacion_exitosa,
          tipo_notificacion_id: editingNotificacion.tipo_notificacion_id || 0,
        });
        setSelectedFile(null);
        setSelectedFileCitacion(null);
      } else {
        setNotificacionForm({
          involucrado_id: 0,
          numerado: "",
          fecha_numerado: "",
          fecha_envio_citacion: "",
          fecha_constancia_citacion: "",
          notificacion_exitosa: false,
          tipo_notificacion_id: 0,
        });
        setSelectedFile(null);
        setSelectedFileCitacion(null);
      }
      setIsSubmitting(false);
    }
  }, [isOpen, editingNotificacion]);

  // Si no hay fecha de constancia, desmarcar notificación exitosa y limpiar tipo
  useEffect(() => {
    if (!notificacionForm.fecha_constancia_citacion) {
      setNotificacionForm((prev) => ({
        ...prev,
        notificacion_exitosa: false,
        tipo_notificacion_id: 0,
      }));
    }
  }, [notificacionForm.fecha_constancia_citacion]);

  // Si se desmarca notificación exitosa, limpiar tipo
  useEffect(() => {
    if (!notificacionForm.notificacion_exitosa) {
      setNotificacionForm((prev) => ({
        ...prev,
        tipo_notificacion_id: 0,
      }));
    }
  }, [notificacionForm.notificacion_exitosa]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Solo permitir PDF
      if (file.type !== "application/pdf") {
        setErrors((prev) => ({
          ...prev,
          file: "Solo se permiten archivos PDF",
        }));
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      if (file.size > 10 * 1024 * 1024) {
        setErrors((prev) => ({
          ...prev,
          file: "El archivo no debe superar los 10MB",
        }));
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        return;
      }

      setSelectedFile(file);
      if (errors.file) {
        setErrors((prev) => ({ ...prev, file: "" }));
      }
    }
  };

  const handleFileCitacionChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Solo permitir PDF
      if (file.type !== "application/pdf") {
        setErrors((prev) => ({
          ...prev,
          file_citacion: "Solo se permiten archivos PDF",
        }));
        if (fileCitacionInputRef.current) {
          fileCitacionInputRef.current.value = "";
        }
        return;
      }

      if (file.size > 10 * 1024 * 1024) {
        setErrors((prev) => ({
          ...prev,
          file_citacion: "El archivo no debe superar los 10MB",
        }));
        if (fileCitacionInputRef.current) {
          fileCitacionInputRef.current.value = "";
        }
        return;
      }

      setSelectedFileCitacion(file);
      if (errors.file_citacion) {
        setErrors((prev) => ({ ...prev, file_citacion: "" }));
      }
    }
  };

  const handleNumeradoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (/^\d{0,4}$/.test(value)) {
      setNotificacionForm({ ...notificacionForm, numerado: value });
      if (errors.numerado) {
        setErrors((prev) => ({ ...prev, numerado: "" }));
      }
    }
  };

  const validateForm = () => {
    const newErrors = {
      involucrado_id: "",
      numerado: "",
      fecha_numerado: "",
      fecha_envio_citacion: "",
      fecha_constancia_citacion: "",
      tipo_notificacion_id: "",
      file: "",
      file_citacion: "",
      general: "",
    };

    let isValid = true;

    // Validar involucrado (solo en creación)
    if (!isEditing && notificacionForm.involucrado_id === 0) {
      newErrors.involucrado_id = "Debe seleccionar un involucrado";
      isValid = false;
    }

    // Validar numerado
    const numeradoTrimmed = notificacionForm.numerado.trim();
    if (!numeradoTrimmed) {
      newErrors.numerado = "El numerado es requerido";
      isValid = false;
    } else if (numeradoTrimmed.length !== 4) {
      newErrors.numerado = "El numerado debe tener exactamente 4 dígitos";
      isValid = false;
    } else if (!/^\d{4}$/.test(numeradoTrimmed)) {
      newErrors.numerado = "El numerado debe contener solo dígitos";
      isValid = false;
    }

    // Validar fecha de numeración
    if (!notificacionForm.fecha_numerado) {
      newErrors.fecha_numerado = "La fecha de numeración es requerida";
      isValid = false;
    }

    // Validar fecha de envío
    if (!notificacionForm.fecha_envio_citacion) {
      newErrors.fecha_envio_citacion = "La fecha de envío es requerida";
      isValid = false;
    }

    // Validar tipo de notificación si es exitosa
    if (
      notificacionForm.notificacion_exitosa &&
      notificacionForm.tipo_notificacion_id === 0
    ) {
      newErrors.tipo_notificacion_id =
        "Debe seleccionar un tipo de notificación";
      isValid = false;
    }

    // Validar documento (solo en creación)
    if (!isEditing && !selectedFile) {
      newErrors.file = "Debe cargar un documento";
      isValid = false;
    }

    // Validar documento de citación (solo en creación)
    if (!isEditing && !selectedFileCitacion) {
      newErrors.file_citacion = "Debe cargar el documento de citación";
      isValid = false;
    }

    setErrors(newErrors);
    return isValid;
  };

  const handleSave = async () => {
    console.log("[NotificationModal] Iniciando guardado...");
    console.log(
      "[NotificationModal] Modo:",
      isEditing ? "EDICIÓN" : "CREACIÓN",
    );

    // Limpiar errores previos
    setErrors({
      involucrado_id: "",
      numerado: "",
      fecha_numerado: "",
      fecha_envio_citacion: "",
      fecha_constancia_citacion: "",
      tipo_notificacion_id: "",
      file: "",
      file_citacion: "",
      general: "",
    });

    // Validar formulario
    if (!validateForm()) {
      console.log("[NotificationModal] Validación fallida");
      return;
    }

    setIsSubmitting(true);

    try {
      // Preparar FormData
      const formData = new FormData();

      // Solo incluir involucrado_id al crear
      if (!isEditing) {
        formData.append(
          "involucrado_id",
          notificacionForm.involucrado_id.toString(),
        );
      }

      formData.append("numerado", notificacionForm.numerado.trim());
      formData.append("fecha_numerado", notificacionForm.fecha_numerado);
      formData.append(
        "fecha_envio_citacion",
        notificacionForm.fecha_envio_citacion,
      );

      if (notificacionForm.fecha_constancia_citacion) {
        formData.append(
          "fecha_constancia_citacion",
          notificacionForm.fecha_constancia_citacion,
        );
      }

      formData.append(
        "notificacion_exitosa",
        notificacionForm.notificacion_exitosa.toString(),
      );

      if (
        notificacionForm.notificacion_exitosa &&
        notificacionForm.tipo_notificacion_id
      ) {
        formData.append(
          "tipo_notificacion_id",
          notificacionForm.tipo_notificacion_id.toString(),
        );
      }

      // Incluir archivo de notificación
      if (selectedFile) {
        formData.append("file", selectedFile);
      }

      // Incluir archivo de citación
      if (selectedFileCitacion) {
        formData.append("file_citacion", selectedFileCitacion);
      }

      console.log("[NotificationModal] Llamando onSave...");
      const result = await onSave(formData);
      console.log("[NotificationModal] Resultado de onSave:", result);

      // Verificar que el resultado sea exitoso
      if (result && result.ok === true) {
        console.log("[NotificationModal] Guardado exitoso, cerrando modal...");
        handleClose();
      } else {
        // Mostrar error específico
        const errorMessage =
          result?.error || "Error desconocido al guardar la notificación";
        console.error("[NotificationModal] Error al guardar:", errorMessage);
        setErrors((prev) => ({
          ...prev,
          general: errorMessage,
        }));
      }
    } catch (error) {
      console.error("[NotificationModal] Excepción capturada:", error);
      setErrors((prev) => ({
        ...prev,
        general:
          error instanceof Error
            ? error.message
            : "Error de conexión al guardar la notificación",
      }));
    } finally {
      console.log(
        "[NotificationModal] Finalizando guardado, isSubmitting = false",
      );
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setNotificacionForm({
      involucrado_id: 0,
      numerado: "",
      fecha_numerado: "",
      fecha_envio_citacion: "",
      fecha_constancia_citacion: "",
      notificacion_exitosa: false,
      tipo_notificacion_id: 0,
    });
    setSelectedFile(null);
    setSelectedFileCitacion(null);
    setErrors({
      involucrado_id: "",
      numerado: "",
      fecha_numerado: "",
      fecha_envio_citacion: "",
      fecha_constancia_citacion: "",
      tipo_notificacion_id: "",
      file: "",
      file_citacion: "",
      general: "",
    });
    setIsSubmitting(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    if (fileCitacionInputRef.current) {
      fileCitacionInputRef.current.value = "";
    }
    onClose();
  };

  // Función para formatear el número de documento con DV para NITs
  const formatDocumentNumber = (involucrado: Involved): string => {
    if (
      involucrado.tipo_documento === "NIT" &&
      involucrado.digito_verificacion
    ) {
      return `${involucrado.numero_documento}-${involucrado.digito_verificacion}`;
    }
    return involucrado.numero_documento.toString();
  };

  if (!isOpen) return null;

  const involucradosDisponibles = involucrados.filter((inv) =>
    editingNotificacion
      ? inv.id === editingNotificacion.involucrado_id
      : !yaNotificados.includes(inv.id),
  );

  // Verificar si hay documento de citación (ya cargado o seleccionado)
  const hasDocumentoCitacion = isEditing
    ? editingNotificacion?.url_doc_citacion || selectedFileCitacion
    : selectedFileCitacion;

  const modalContent = (
    <div
      data-theme={theme}
      className="fixed inset-0 z-[999999] flex items-center justify-center select-none bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={handleClose}
    >
      <div
        className="bg-base-100 rounded-2xl w-full max-w-2xl mx-4 shadow-2xl border border-base-300 animate-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="relative px-6 py-5 border-b border-base-300">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-success/10 rounded-xl flex items-center justify-center">
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
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                />
              </svg>
            </div>
            <div>
              <h3 className="font-bold text-lg text-base-content">
                {editingNotificacion
                  ? "Editar Notificación"
                  : "Nueva Notificación"}
              </h3>
              <p className="text-xs text-base-content/60">
                Complete la información de la notificación
              </p>
            </div>
          </div>

          <button
            onClick={handleClose}
            className="absolute top-4 right-4 btn btn-ghost btn-sm btn-circle"
            disabled={isSubmitting}
          >
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {/* Involucrado a Notificar - Solo en creación */}
          {!editingNotificacion && (
            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Involucrado a Notificar
                  <span className="text-error ml-1">*</span>
                </span>
              </label>
              <select
                value={notificacionForm.involucrado_id}
                onChange={(e) =>
                  setNotificacionForm({
                    ...notificacionForm,
                    involucrado_id: Number(e.target.value),
                  })
                }
                className={`select select-bordered w-full ${
                  errors.involucrado_id
                    ? "select-error"
                    : "focus:select-success"
                }`}
                disabled={isSubmitting}
              >
                <option value={0}>Seleccione un involucrado</option>
                {involucradosDisponibles.map((involucrado) => (
                  <option key={involucrado.id} value={involucrado.id}>
                    {involucrado.nombre} ({involucrado.tipo_documento}:{" "}
                    {formatDocumentNumber(involucrado)})
                  </option>
                ))}
              </select>
              {errors.involucrado_id && (
                <label className="label">
                  <span className="label-text-alt text-error">
                    {errors.involucrado_id}
                  </span>
                </label>
              )}
            </div>
          )}

          {/* Numerado y Fecha Numerado */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Numerado{" "}
                  <span className="text-xs text-base-content/50">
                    (4 dígitos)
                  </span>
                  <span className="text-error ml-1">*</span>
                </span>
              </label>
              <input
                type="text"
                value={notificacionForm.numerado}
                onChange={handleNumeradoChange}
                className={`input input-bordered w-full font-mono ${
                  errors.numerado ? "input-error" : "focus:input-success"
                }`}
                placeholder="0001"
                maxLength={4}
                disabled={isSubmitting}
              />
              {errors.numerado && (
                <label className="label">
                  <span className="label-text-alt text-error">
                    {errors.numerado}
                  </span>
                </label>
              )}
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Fecha Numerado
                  <span className="text-error ml-1">*</span>
                </span>
              </label>
              <input
                type="date"
                value={notificacionForm.fecha_numerado}
                onChange={(e) => {
                  setNotificacionForm({
                    ...notificacionForm,
                    fecha_numerado: e.target.value,
                  });
                  if (errors.fecha_numerado) {
                    setErrors((prev) => ({ ...prev, fecha_numerado: "" }));
                  }
                }}
                className={`input input-bordered w-full ${
                  errors.fecha_numerado ? "input-error" : "focus:input-success"
                }`}
                disabled={isSubmitting}
              />
              {errors.fecha_numerado && (
                <label className="label">
                  <span className="label-text-alt text-error">
                    {errors.fecha_numerado}
                  </span>
                </label>
              )}
            </div>
          </div>

          {/* Fecha Envío Citación y Fecha Constancia Citación */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Fecha Envío Citación
                  <span className="text-error ml-1">*</span>
                </span>
              </label>
              <input
                type="date"
                value={notificacionForm.fecha_envio_citacion}
                onChange={(e) => {
                  setNotificacionForm({
                    ...notificacionForm,
                    fecha_envio_citacion: e.target.value,
                  });
                  if (errors.fecha_envio_citacion) {
                    setErrors((prev) => ({
                      ...prev,
                      fecha_envio_citacion: "",
                    }));
                  }
                }}
                className={`input input-bordered w-full ${
                  errors.fecha_envio_citacion
                    ? "input-error"
                    : "focus:input-success"
                }`}
                disabled={isSubmitting}
              />
              {errors.fecha_envio_citacion && (
                <label className="label">
                  <span className="label-text-alt text-error">
                    {errors.fecha_envio_citacion}
                  </span>
                </label>
              )}
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Fecha Constancia Citación
                </span>
              </label>
              <input
                type="date"
                value={notificacionForm.fecha_constancia_citacion}
                onChange={(e) =>
                  setNotificacionForm({
                    ...notificacionForm,
                    fecha_constancia_citacion: e.target.value,
                  })
                }
                className="input input-bordered w-full focus:input-success"
                disabled={isSubmitting}
              />
            </div>
          </div>

          {/* Documento Citación */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Documento Citación
                {!isEditing && <span className="text-error ml-1">*</span>}
                <span className="text-xs text-base-content/50 ml-2">
                  (PDF - Máx. 10MB)
                </span>
              </span>
            </label>
            <input
              ref={fileCitacionInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className={`file-input file-input-bordered w-full ${
                errors.file_citacion ? "file-input-error" : ""
              }`}
              onChange={handleFileCitacionChange}
              disabled={isSubmitting}
            />
            {errors.file_citacion && (
              <label className="label">
                <span className="label-text-alt text-error">
                  {errors.file_citacion}
                </span>
              </label>
            )}
            {selectedFileCitacion && !errors.file_citacion && (
              <label className="label">
                <span className="label-text-alt text-success flex items-center gap-1">
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
                  {selectedFileCitacion.name}
                </span>
              </label>
            )}
            {isEditing &&
              !selectedFileCitacion &&
              editingNotificacion?.url_doc_citacion && (
                <label className="label">
                  <span className="label-text-alt text-info">
                    Opcional - Solo si desea reemplazar el documento actual
                  </span>
                </label>
              )}
            {isEditing &&
              !selectedFileCitacion &&
              !editingNotificacion?.url_doc_citacion && (
                <label className="label">
                  <span className="label-text-alt text-warning">
                    ⚠️ No hay documento de citación cargado. Debe subir uno para
                    habilitar la sección de notificación.
                  </span>
                </label>
              )}
          </div>

          {/* Separador visual */}
          {(editingNotificacion?.url_doc_citacion ||
            selectedFileCitacion ||
            !isEditing) && (
            <div className="divider text-sm text-base-content/50">
              Información de Notificación
            </div>
          )}

          {/* Citación Exitosa y Tipo Notificación */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Notificación Exitosa
                </span>
              </label>
              <label
                className={`flex items-center h-12 px-4 rounded-lg border-2 ${
                  !hasDocumentoCitacion ||
                  !notificacionForm.fecha_constancia_citacion
                    ? "opacity-50 cursor-not-allowed bg-base-200 border-base-300"
                    : notificacionForm.notificacion_exitosa
                      ? "border-success bg-success/5 cursor-pointer"
                      : "border-base-300 hover:border-success/30 hover:bg-success/5 cursor-pointer"
                }`}
              >
                <input
                  type="checkbox"
                  checked={notificacionForm.notificacion_exitosa}
                  onChange={(e) =>
                    setNotificacionForm({
                      ...notificacionForm,
                      notificacion_exitosa: e.target.checked,
                    })
                  }
                  className="checkbox checkbox-success"
                  disabled={
                    !hasDocumentoCitacion ||
                    !notificacionForm.fecha_constancia_citacion ||
                    isSubmitting
                  }
                />
                <span className="ml-3 text-sm font-medium">
                  {!hasDocumentoCitacion
                    ? "Requiere documento de citación"
                    : !notificacionForm.fecha_constancia_citacion
                      ? "Requiere fecha de constancia"
                      : "Notificación entregada"}
                </span>
              </label>
            </div>

            <div className="form-control">
              <label className="label">
                <span className="label-text font-medium">
                  Tipo Notificación
                  {notificacionForm.notificacion_exitosa && (
                    <span className="text-error ml-1">*</span>
                  )}
                </span>
              </label>
              <div className="relative">
                <select
                  value={notificacionForm.tipo_notificacion_id}
                  onChange={(e) => {
                    setNotificacionForm({
                      ...notificacionForm,
                      tipo_notificacion_id: Number(e.target.value),
                    });
                    if (errors.tipo_notificacion_id) {
                      setErrors((prev) => ({
                        ...prev,
                        tipo_notificacion_id: "",
                      }));
                    }
                  }}
                  className={`select select-bordered w-full h-12 ${
                    errors.tipo_notificacion_id
                      ? "select-error border-2"
                      : notificacionForm.tipo_notificacion_id !== 0
                        ? "border-2 border-success"
                        : "focus:select-success"
                  } ${
                    !hasDocumentoCitacion ||
                    !notificacionForm.notificacion_exitosa
                      ? "opacity-50 cursor-not-allowed"
                      : ""
                  }`}
                  disabled={
                    !hasDocumentoCitacion ||
                    !notificacionForm.notificacion_exitosa ||
                    isSubmitting
                  }
                >
                  <option value={0}>
                    {!hasDocumentoCitacion
                      ? "Requiere documento de citación"
                      : !notificacionForm.notificacion_exitosa
                        ? "Marque citación exitosa primero"
                        : "Seleccione un tipo"}
                  </option>
                  {tiposNotificacion.map((tipo) => (
                    <option key={tipo.id} value={tipo.id}>
                      {tipo.nombre}
                    </option>
                  ))}
                </select>
              </div>
              {errors.tipo_notificacion_id && (
                <label className="label">
                  <span className="label-text-alt text-error">
                    {errors.tipo_notificacion_id}
                  </span>
                </label>
              )}
            </div>
          </div>

          {/* Documento */}
          <div className="form-control">
            <label className="label">
              <span className="label-text font-medium">
                Documento
                {!isEditing && <span className="text-error ml-1">*</span>}
                <span className="text-xs text-base-content/50 ml-2">
                  (PDF - Máx. 10MB)
                </span>
              </span>
            </label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className={`file-input file-input-bordered w-full ${
                errors.file ? "file-input-error" : ""
              } ${!hasDocumentoCitacion ? "opacity-50 cursor-not-allowed" : ""}`}
              onChange={handleFileChange}
              disabled={!hasDocumentoCitacion || isSubmitting}
            />
            {errors.file && (
              <label className="label">
                <span className="label-text-alt text-error">{errors.file}</span>
              </label>
            )}
            {selectedFile && !errors.file && (
              <label className="label">
                <span className="label-text-alt text-success flex items-center gap-1">
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
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  {selectedFile.name}
                </span>
              </label>
            )}
            {isEditing && !selectedFile && (
              <label className="label">
                <span className="label-text-alt text-base-content/60">
                  Opcional - Solo si desea reemplazar el documento
                </span>
              </label>
            )}
          </div>

          {/* Error general */}
          {errors.general && (
            <div className="alert alert-error">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="stroke-current shrink-0 h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span>{errors.general}</span>
            </div>
          )}

          {/* Botones */}
          <div className="flex justify-end space-x-2 pt-4 border-t border-base-300">
            <button
              type="button"
              onClick={handleClose}
              className="btn btn-ghost"
              disabled={isSubmitting}
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="btn btn-success text-white gap-2"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <span className="loading loading-spinner loading-sm"></span>
                  Guardando...
                </>
              ) : isEditing ? (
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
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  Actualizar
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
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                  Agregar
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
}
