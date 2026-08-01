import { useState, useEffect, useRef } from "react";
import type { InvolucradoNotificacion } from "../../../types/sancionatorioApp";
import {
  uploadFileToDocuments,
  generateDocumentFileName,
  validateFile,
} from "../../../utils/fileUpload";
import type { NotificacionFormData } from "./actoAdminConfig";

export type NotificacionFormValues = {
  involucrado_id: number;
  numerado: string;
  fecha_numerado: string;
  fecha_envio_citacion: string;
  fecha_constancia_citacion: string;
  notificacion_exitosa: boolean;
  tipo_notificacion_id: number;
};

export type NotificacionFormErrors = {
  involucrado_id: string;
  numerado: string;
  fecha_numerado: string;
  fecha_envio_citacion: string;
  fecha_constancia_citacion: string;
  tipo_notificacion_id: string;
  file: string;
  file_citacion: string;
  general: string;
};

const EMPTY_FORM: NotificacionFormValues = {
  involucrado_id: 0,
  numerado: "",
  fecha_numerado: "",
  fecha_envio_citacion: "",
  fecha_constancia_citacion: "",
  notificacion_exitosa: false,
  tipo_notificacion_id: 0,
};

const EMPTY_ERRORS: NotificacionFormErrors = {
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

type Params = {
  isOpen: boolean;
  editingNotificacion: InvolucradoNotificacion | null;
  onSave: (data: NotificacionFormData) => Promise<{
    ok: boolean;
    error?: string;
  }>;
  onClose: () => void;
};

/** Estado, validación, carga de archivos y guardado del formulario de notificación. */
export function useNotificacionForm({
  isOpen,
  editingNotificacion,
  onSave,
  onClose,
}: Params) {
  const [notificacionForm, setNotificacionForm] =
    useState<NotificacionFormValues>({ ...EMPTY_FORM });
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedFileCitacion, setSelectedFileCitacion] = useState<File | null>(
    null,
  );
  const [errors, setErrors] = useState<NotificacionFormErrors>({
    ...EMPTY_ERRORS,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingFiles, setIsUploadingFiles] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const fileCitacionInputRef = useRef<HTMLInputElement>(null);

  const isEditing = !!editingNotificacion;

  useEffect(() => {
    if (isOpen) {
      setErrors({ ...EMPTY_ERRORS });

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
        setNotificacionForm({ ...EMPTY_FORM });
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
      const validation = validateFile(file);
      if (!validation.isValid) {
        setErrors((prev) => ({
          ...prev,
          file: validation.error || "Archivo inválido",
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
      const validation = validateFile(file);
      if (!validation.isValid) {
        setErrors((prev) => ({
          ...prev,
          file_citacion: validation.error || "Archivo inválido",
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
    const newErrors: NotificacionFormErrors = { ...EMPTY_ERRORS };

    let isValid = true;

    // Validar involucrado (solo en creación)
    if (!isEditing && notificacionForm.involucrado_id === 0) {
      newErrors.involucrado_id = "Debe seleccionar un involucrado";
      isValid = false;
    }

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

    if (!notificacionForm.fecha_numerado) {
      newErrors.fecha_numerado = "La fecha de numeración es requerida";
      isValid = false;
    }

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

    // Validar documento cuando notificacion_exitosa es true
    if (notificacionForm.notificacion_exitosa) {
      const tieneDocumentoExistente =
        isEditing && editingNotificacion?.documento_notificacion_id;
      if (!selectedFile && !tieneDocumentoExistente) {
        newErrors.file = "Debe cargar un documento de notificación";
        isValid = false;
      }
    }

    // Validar documento de citación (solo en creación)
    if (!isEditing && !selectedFileCitacion) {
      newErrors.file_citacion = "Debe cargar el documento de citación";
      isValid = false;
    }

    setErrors(newErrors);
    return isValid;
  };

  const handleClose = () => {
    setNotificacionForm({ ...EMPTY_FORM });
    setSelectedFile(null);
    setSelectedFileCitacion(null);
    setErrors({ ...EMPTY_ERRORS });
    setIsSubmitting(false);
    setIsUploadingFiles(false);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    if (fileCitacionInputRef.current) {
      fileCitacionInputRef.current.value = "";
    }
    onClose();
  };

  const handleSave = async () => {
    setErrors({ ...EMPTY_ERRORS });

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      let documento_notificacion_id: number | undefined;
      let documento_citacion_id: number | undefined;

      setIsUploadingFiles(true);

      // Paso 1: Subir archivos en paralelo si existen
      const uploadPromises: Promise<{
        type: "notificacion" | "citacion";
        fileId: number;
      }>[] = [];

      if (selectedFile) {
        const fileName = generateDocumentFileName(
          "NOTIF",
          notificacionForm.numerado,
          notificacionForm.fecha_numerado,
        );

        uploadPromises.push(
          uploadFileToDocuments(selectedFile, fileName).then((fileId) => ({
            type: "notificacion" as const,
            fileId,
          })),
        );
      }

      if (selectedFileCitacion) {
        const fileName = generateDocumentFileName(
          "CITAC",
          notificacionForm.numerado,
          notificacionForm.fecha_numerado,
        );

        uploadPromises.push(
          uploadFileToDocuments(selectedFileCitacion, fileName).then(
            (fileId) => ({
              type: "citacion" as const,
              fileId,
            }),
          ),
        );
      }

      // Esperar a que todos los uploads terminen en paralelo
      if (uploadPromises.length > 0) {
        try {
          const uploadResults = await Promise.all(uploadPromises);

          uploadResults.forEach((result) => {
            if (result.type === "notificacion") {
              documento_notificacion_id = result.fileId;
            } else {
              documento_citacion_id = result.fileId;
            }
          });
        } catch (uploadError) {
          throw new Error(
            uploadError instanceof Error
              ? uploadError.message
              : "Error al subir los archivos",
          );
        }
      }

      setIsUploadingFiles(false);

      // Paso 3: Preparar datos para enviar
      const notificationData = {
        numerado: notificacionForm.numerado.trim(),
        fecha_numerado: notificacionForm.fecha_numerado,
        fecha_envio_citacion: notificacionForm.fecha_envio_citacion,
        fecha_constancia_citacion:
          notificacionForm.fecha_constancia_citacion || "",
        notificacion_exitosa: notificacionForm.notificacion_exitosa,
        ...(documento_notificacion_id && { documento_notificacion_id }),
        ...(documento_citacion_id && { documento_citacion_id }),
        ...(notificacionForm.notificacion_exitosa &&
          notificacionForm.tipo_notificacion_id && {
            tipo_notificacion_id: notificacionForm.tipo_notificacion_id,
          }),
        ...(notificacionForm.notificacion_exitosa &&
          notificacionForm.fecha_constancia_citacion && {
            fecha_notificacion: notificacionForm.fecha_constancia_citacion,
          }),
        ...(!isEditing && { involucrado_id: notificacionForm.involucrado_id }),
      };

      const result = await onSave(notificationData);

      if (result && result.ok === true) {
        handleClose();
      } else {
        const errorMessage =
          result?.error || "Error desconocido al guardar la notificación";
        setErrors((prev) => ({
          ...prev,
          general: errorMessage,
        }));
      }
    } catch (error) {
      setErrors((prev) => ({
        ...prev,
        general:
          error instanceof Error
            ? error.message
            : "Error de conexión al guardar la notificación",
      }));
    } finally {
      setIsSubmitting(false);
      setIsUploadingFiles(false);
    }
  };

  return {
    notificacionForm,
    setNotificacionForm,
    errors,
    setErrors,
    selectedFile,
    selectedFileCitacion,
    isSubmitting,
    isUploadingFiles,
    isEditing,
    fileInputRef,
    fileCitacionInputRef,
    handleFileChange,
    handleFileCitacionChange,
    handleNumeradoChange,
    handleSave,
    handleClose,
  };
}

export type NotificacionFormApi = ReturnType<typeof useNotificacionForm>;
