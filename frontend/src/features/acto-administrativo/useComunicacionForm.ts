import { useEffect, useRef, useState } from "react";
import { apiCall, formatApiErrorDetail } from "@shared/lib/api";
import {
  uploadFileToDocuments,
  generateDocumentFileName,
} from "@shared/lib/fileUpload";
import type { ComunicacionData } from "./actoAdminConfig";

type ComunicacionErrors = {
  numerado: string;
  fecha_numerado: string;
  fecha_envio: string;
  file: string;
  general: string;
};

const EMPTY_ERRORS: ComunicacionErrors = {
  numerado: "",
  fecha_numerado: "",
  fecha_envio: "",
  file: "",
  general: "",
};

const VALID_FILE_TYPES = ["application/pdf", "image/jpeg", "image/png"];
const MAX_FILE_SIZE = 10 * 1024 * 1024;

type Params = {
  isOpen: boolean;
  onClose: () => void;
  expedienteId: number;
  actoAdminId: number;
  editComunicacion?: ComunicacionData | null;
  onSuccess?: (comunicacionData: ComunicacionData) => void;
  endpoints: {
    create: string;
    update: (comunicacionId: number) => string;
  };
};

/** Estado, validación y guardado del formulario de comunicación. */
export function useComunicacionForm({
  isOpen,
  onClose,
  expedienteId,
  actoAdminId,
  editComunicacion,
  onSuccess,
  endpoints,
}: Params) {
  const [numerado, setNumerado] = useState("");
  const [fechaNumerado, setFechaNumerado] = useState("");
  const [fechaEnvio, setFechaEnvio] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<ComunicacionErrors>(EMPTY_ERRORS);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isEditing = !!editComunicacion;

  useEffect(() => {
    if (!isOpen) return;
    setErrors(EMPTY_ERRORS);
    if (editComunicacion) {
      setNumerado(String(editComunicacion.numerado).padStart(4, "0"));
      setFechaNumerado(editComunicacion.fecha_numerado);
      setFechaEnvio(editComunicacion.fecha_envio);
    } else {
      setNumerado("");
      setFechaNumerado("");
      setFechaEnvio("");
    }
    setSelectedFile(null);
    setIsSubmitting(false);
    setIsUploadingFile(false);
  }, [isOpen, editComunicacion]);

  const clearFileInput = () => {
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const clearError = (field: keyof ComunicacionErrors) => {
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: "" }));
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (!VALID_FILE_TYPES.includes(file.type)) {
      setErrors((prev) => ({
        ...prev,
        file: "Solo se permiten archivos PDF, JPG o PNG",
      }));
      clearFileInput();
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setErrors((prev) => ({
        ...prev,
        file: "El archivo no debe superar los 10MB",
      }));
      clearFileInput();
      return;
    }

    setSelectedFile(file);
    clearError("file");
  };

  const handleNumeradoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    if (/^\d{0,4}$/.test(value)) {
      setNumerado(value);
      clearError("numerado");
    }
  };

  const handleFechaNumeradoChange = (value: string) => {
    setFechaNumerado(value);
    clearError("fecha_numerado");
  };

  const handleFechaEnvioChange = (value: string) => {
    setFechaEnvio(value);
    clearError("fecha_envio");
  };

  const validateForm = () => {
    const newErrors = { ...EMPTY_ERRORS };
    let isValid = true;

    if (!numerado) {
      newErrors.numerado = "El numerado es requerido";
      isValid = false;
    } else if (numerado.length !== 4) {
      newErrors.numerado = "El numerado debe tener exactamente 4 dígitos";
      isValid = false;
    } else if (!/^\d{4}$/.test(numerado)) {
      newErrors.numerado = "El numerado debe contener solo números";
      isValid = false;
    }

    if (!fechaNumerado) {
      newErrors.fecha_numerado = "La fecha de numeración es requerida";
      isValid = false;
    }

    if (!fechaEnvio) {
      newErrors.fecha_envio = "La fecha de envío es requerida";
      isValid = false;
    }

    // Documento: requerido en creación, opcional en edición.
    if (!isEditing && !selectedFile) {
      newErrors.file = "Debe cargar un documento";
      isValid = false;
    }

    setErrors(newErrors);
    return isValid;
  };

  const handleClose = () => {
    setNumerado("");
    setFechaNumerado("");
    setFechaEnvio("");
    setSelectedFile(null);
    setErrors(EMPTY_ERRORS);
    setIsSubmitting(false);
    setIsUploadingFile(false);
    clearFileInput();
    onClose();
  };

  const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrors(EMPTY_ERRORS);
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      let documentoComunicacionId = editComunicacion?.documento_comunicacion_id;

      // Si llega nuevo archivo, primero subirlo a app-docs y esperar su file_id.
      if (selectedFile) {
        setIsUploadingFile(true);
        try {
          const fileName = generateDocumentFileName(
            "COM",
            numerado,
            fechaNumerado,
          );
          documentoComunicacionId = await uploadFileToDocuments(
            selectedFile,
            fileName,
          );
        } finally {
          setIsUploadingFile(false);
        }
      }

      if (!documentoComunicacionId) {
        throw new Error("No se pudo obtener el ID del documento");
      }

      const formData = new FormData();
      formData.append("expediente_id", expedienteId.toString());
      formData.append("acto_admin_id", actoAdminId.toString());
      formData.append("numerado", numerado);
      formData.append("fecha_numerado", fechaNumerado);
      formData.append("fecha_envio", fechaEnvio);
      formData.append(
        "documento_comunicacion_id",
        documentoComunicacionId.toString(),
      );

      const res = await apiCall(
        editComunicacion
          ? endpoints.update(editComunicacion.id)
          : endpoints.create,
        { method: editComunicacion ? "PUT" : "POST", body: formData },
      );

      if (res.ok) {
        onSuccess?.(res.data);
        handleClose();
      } else {
        setErrors((prev) => ({
          ...prev,
          general: formatApiErrorDetail(
            res.detail,
            "Error al guardar la comunicación",
          ),
        }));
      }
    } catch (error) {
      // Antes se ocultaba el motivo real (p. ej. fallo de subida a app-docs).
      setErrors((prev) => ({
        ...prev,
        general:
          error instanceof Error && error.message
            ? error.message
            : "Error de conexión al guardar la comunicación",
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    numerado,
    fechaNumerado,
    fechaEnvio,
    selectedFile,
    errors,
    isSubmitting,
    isUploadingFile,
    isEditing,
    fileInputRef,
    handleFileChange,
    handleNumeradoChange,
    handleFechaNumeradoChange,
    handleFechaEnvioChange,
    handleSave,
    handleClose,
  };
}
