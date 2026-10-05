import { useEffect, useRef, useState } from "react";
import { uploadFileToDocuments, validateFile } from "@shared/lib/fileUpload";
import type { DocumentoAnexo, DocumentoAnexoPayload } from "../../types";

type Errores = { tipo: string; nombre: string; file: string; general: string };

const SIN_ERRORES: Errores = { tipo: "", nombre: "", file: "", general: "" };
const MSG_NOMBRE_VACIO = "Debe ingresar un nombre para el documento";
const MSG_NOMBRE_REPETIDO = "Este nombre ya existe en los tipos de documento. Use el selector.";

type Params = {
  isOpen: boolean;
  onClose: () => void;
  onSave: (data: DocumentoAnexoPayload) => Promise<{ ok: boolean; error?: string }>;
  editDocumento: DocumentoAnexo | null;
  tiposDocumento: string[];
};

/** Estado, validación y guardado del formulario de documento anexo. */
export function useDocumentoForm({ isOpen, onClose, onSave, editDocumento, tiposDocumento }: Params) {
  const [tipoDocumento, setTipoDocumento] = useState("");
  const [nombrePersonalizado, setNombrePersonalizado] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<Errores>(SIN_ERRORES);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isUploadingFile, setIsUploadingFile] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const isEditing = !!editDocumento;
  const isOtroSelected = tipoDocumento === "Otro";
  const nombreRepetido = (valor: string) =>
    tiposDocumento.some((tipo) => tipo.toLowerCase() === valor.trim().toLowerCase());

  useEffect(() => {
    if (!isOpen) return;
    setErrors(SIN_ERRORES);
    if (editDocumento) {
      // Si el nombre no es un tipo predefinido, es un "Otro" personalizado.
      const predefinido = tiposDocumento.includes(editDocumento.nombre);
      setTipoDocumento(predefinido ? editDocumento.nombre : "Otro");
      setNombrePersonalizado(predefinido ? "" : editDocumento.nombre);
    } else {
      setTipoDocumento("");
      setNombrePersonalizado("");
    }
    setSelectedFile(null);
    setIsSubmitting(false);
  }, [isOpen, editDocumento, tiposDocumento]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const validation = validateFile(file);
    if (!validation.isValid) {
      setErrors((prev) => ({ ...prev, file: validation.error || "Archivo inválido" }));
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }
    setSelectedFile(file);
    if (errors.file) setErrors((prev) => ({ ...prev, file: "" }));
  };

  const handleTipoChange = (value: string) => {
    setTipoDocumento(value);
    if (errors.tipo) setErrors((prev) => ({ ...prev, tipo: "" }));
    // Limpiar nombre personalizado si no es "Otro"
    if (value !== "Otro") {
      setNombrePersonalizado("");
      if (errors.nombre) setErrors((prev) => ({ ...prev, nombre: "" }));
    }
  };

  const handleNombrePersonalizadoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const valor = e.target.value;
    setNombrePersonalizado(valor);
    if (valor.trim()) {
      if (nombreRepetido(valor)) {
        setErrors((prev) => ({ ...prev, nombre: MSG_NOMBRE_REPETIDO }));
      } else if (errors.nombre) {
        setErrors((prev) => ({ ...prev, nombre: "" }));
      }
    } else if (errors.nombre && errors.nombre !== MSG_NOMBRE_VACIO) {
      setErrors((prev) => ({ ...prev, nombre: "" }));
    }
  };

  const validateForm = () => {
    const nuevos = { ...SIN_ERRORES };
    if (!tipoDocumento) nuevos.tipo = "Debe seleccionar un tipo de documento";
    if (isOtroSelected) {
      if (!nombrePersonalizado.trim()) nuevos.nombre = MSG_NOMBRE_VACIO;
      else if (nombreRepetido(nombrePersonalizado)) nuevos.nombre = MSG_NOMBRE_REPETIDO;
    }
    // Archivo PDF obligatorio si es nuevo
    if (!isEditing && !selectedFile) nuevos.file = "Debe seleccionar un archivo PDF";
    setErrors(nuevos);
    return !nuevos.tipo && !nuevos.nombre && !nuevos.file;
  };

  const handleClose = () => {
    setTipoDocumento("");
    setNombrePersonalizado("");
    setSelectedFile(null);
    setErrors(SIN_ERRORES);
    setIsSubmitting(false);
    setIsUploadingFile(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
    onClose();
  };

  const handleSave = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setErrors(SIN_ERRORES);
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      const nombreFinal = isOtroSelected ? nombrePersonalizado.trim() : tipoDocumento;
      let documento_anexo_id: number | undefined;

      // Paso 1: si hay archivo, subirlo primero a app-docs
      if (selectedFile) {
        setIsUploadingFile(true);
        try {
          documento_anexo_id = await uploadFileToDocuments(
            selectedFile,
            `${nombreFinal.replace(/\s+/g, "_")}.pdf`,
          );
        } catch (uploadError) {
          throw new Error(
            uploadError instanceof Error
              ? uploadError.message
              : "Error al subir el archivo a la aplicación de documentos",
          );
        } finally {
          setIsUploadingFile(false);
        }
      }

      documento_anexo_id ??= editDocumento?.documento_anexo_id;
      if (!documento_anexo_id) throw new Error("No se encontró el documento adjunto");

      const result = await onSave({ nombre: nombreFinal, documento_anexo_id });
      if (result.ok) {
        handleClose();
      } else {
        setErrors((prev) => ({ ...prev, general: result.error || "Error al guardar el documento" }));
      }
    } catch (error) {
      setErrors((prev) => ({
        ...prev,
        general: error instanceof Error ? error.message : "Error inesperado al guardar el documento",
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  return {
    tipoDocumento,
    nombrePersonalizado,
    selectedFile,
    errors,
    isSubmitting,
    isUploadingFile,
    ocupado: isSubmitting || isUploadingFile,
    isEditing,
    isOtroSelected,
    fileInputRef,
    handleFileChange,
    handleTipoChange,
    handleNombrePersonalizadoChange,
    handleSave,
    handleClose,
  };
}
