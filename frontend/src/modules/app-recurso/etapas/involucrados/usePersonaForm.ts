import { useState } from "react";
import { buscarPersona, PERSONA_VACIA, type PersonaForm } from "../../api/involucrados";
import type { PersonaInvolucrada, SetToast } from "../../types";
import { documentoBuscable, formDesdePersona } from "./personaForm";

/**
 * Estado del formulario de una persona (réplica del de
 * `@features/involucrados-expediente`, que no se exporta): al salir del
 * documento la busca en app-involved y, si existe, autocompleta y bloquea.
 */
export function usePersonaForm(setToast: SetToast, tipoInicial = "CC") {
  const vacio = { ...PERSONA_VACIA, tipo_documento: tipoInicial };
  const [form, setForm] = useState<PersonaForm>(vacio);
  const [existente, setExistente] = useState<PersonaInvolucrada | null>(null);
  const [buscando, setBuscando] = useState(false);

  const setCampo = (campo: keyof PersonaForm, valor: string) => setForm((prev) => ({ ...prev, [campo]: valor }));

  /** Cambiar tipo o número invalida a la persona encontrada. */
  const cambiarDocumento = (cambio: Partial<PersonaForm>) => {
    if (existente) {
      setExistente(null);
      setForm({ ...vacio, ...pick(form), ...cambio });
    } else {
      setForm((prev) => ({ ...prev, ...cambio }));
    }
  };

  const buscar = async () => {
    if (existente || !documentoBuscable(form)) return;
    setBuscando(true);
    try {
      const p = await buscarPersona(
        form.tipo_documento,
        form.numero_documento.trim(),
        form.tipo_documento === "NIT" ? form.digito_verificacion : undefined,
      );
      if (p) setForm(formDesdePersona(p));
      setExistente(p);
    } catch {
      setToast({ id: Date.now(), message: "Servicio de involucrados no disponible", type: "error" });
    } finally {
      setBuscando(false);
    }
  };

  const reset = () => {
    setForm(vacio);
    setExistente(null);
  };

  return { form, existente, buscando, setCampo, cambiarDocumento, buscar, reset };
}

const pick = (f: PersonaForm) => ({
  tipo_documento: f.tipo_documento,
  numero_documento: f.numero_documento,
  digito_verificacion: f.digito_verificacion,
});

export type PersonaFormState = ReturnType<typeof usePersonaForm>;
