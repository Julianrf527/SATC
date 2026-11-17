import { useCallback, useState } from "react";
import type { Involucrado } from "@shared/types/involucrado";
import { getErrorMessage } from "@shared/lib/api";
import { buscarInvolucrado } from "./api/involucrados";
import type { InvolucradoForm, SetToast } from "./types";

export const initialFormData: InvolucradoForm = {
  numero_documento: "",
  digito_verificacion: "",
  tipo_documento: "CC",
  nombre: "",
  celular: "",
  correo: "",
  direccion: "",
};

/**
 * Estado del formulario de vinculación: al salir del campo de documento busca
 * el involucrado en app-involved y, si existe, autocompleta y bloquea datos.
 */
export function useInvolucradoForm(setToast: SetToast) {
  const [formData, setFormData] = useState<InvolucradoForm>(initialFormData);
  const [existingInvolucrado, setExistingInvolucrado] =
    useState<Involucrado | null>(null);
  const [isSearching, setIsSearching] = useState(false);

  const buscar = useCallback(
    async (num: string, tipo: string, dv?: string) => {
      if (!num.trim() || !tipo.trim() || num.length < 7) return;
      if (tipo === "NIT" && !dv?.trim()) return;
      try {
        setIsSearching(true);
        const inv = await buscarInvolucrado(tipo, num, dv);
        if (inv) {
          setFormData({
            numero_documento:
              inv.numero_documento != null ? inv.numero_documento.toString() : "",
            digito_verificacion: inv.digito_verificacion || "",
            tipo_documento: inv.tipo_documento,
            nombre: inv.nombre,
            celular: inv.celular != null ? inv.celular.toString() : "",
            correo: inv.correo ?? "",
            direccion: inv.direccion ?? "",
          });
        }
        setExistingInvolucrado(inv);
      } catch (error) {
        if (!getErrorMessage(error).includes("404"))
          setToast({
            id: Date.now(),
            message: "Servicio de involucrados no disponible",
            type: "error",
          });
      } finally {
        setIsSearching(false);
      }
    },
    [setToast],
  );

  const reset = () => {
    setFormData(initialFormData);
    setExistingInvolucrado(null);
  };

  const setField = (field: keyof InvolucradoForm, value: string) =>
    setFormData((prev) => ({ ...prev, [field]: value }));

  const handleDocumentChange = (value: string) => {
    const v = value.replace(/\D/g, "");
    if (
      existingInvolucrado &&
      v !== existingInvolucrado.numero_documento.toString()
    ) {
      setExistingInvolucrado(null);
      setFormData({
        ...initialFormData,
        numero_documento: v,
        digito_verificacion: formData.digito_verificacion,
        tipo_documento: formData.tipo_documento,
      });
    } else {
      setFormData({ ...formData, numero_documento: v });
    }
  };

  const handleTipoChange = (value: string) => {
    if (existingInvolucrado && value !== existingInvolucrado.tipo_documento) {
      setExistingInvolucrado(null);
      setFormData({
        ...initialFormData,
        tipo_documento: value,
        numero_documento: formData.numero_documento,
      });
    } else {
      setFormData({
        ...formData,
        tipo_documento: value,
        digito_verificacion:
          value === "NIT" ? formData.digito_verificacion : "",
      });
    }
  };

  const triggerSearch = () => {
    if (formData.numero_documento.length < 7 || existingInvolucrado) return;
    if (formData.tipo_documento === "NIT") {
      if (formData.digito_verificacion)
        buscar(
          formData.numero_documento,
          formData.tipo_documento,
          formData.digito_verificacion,
        );
    } else {
      buscar(formData.numero_documento, formData.tipo_documento);
    }
  };

  return {
    formData,
    existingInvolucrado,
    isSearching,
    setField,
    handleDocumentChange,
    handleTipoChange,
    triggerSearch,
    reset,
  };
}

export type InvolucradoFormState = ReturnType<typeof useInvolucradoForm>;
