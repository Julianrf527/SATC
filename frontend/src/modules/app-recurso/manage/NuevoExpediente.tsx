import { useRef, useState, type FormEvent } from "react";
import { NuevoExpedienteLayout } from "@features/expedientes";
import { useCrearExpedienteMutation } from "../api/expedientes";
import { mensajeError } from "../api/errors";
import type { CatalogosRecurso, SetToast } from "../types";
import ExpedienteFields from "./expediente-form/ExpedienteFields";
import { FORM_VACIO, validarExpedienteForm, type ExpedienteFormState } from "./expediente-form/expedienteForm";

type Props = {
  catalogos: CatalogosRecurso;
  setToast: SetToast;
  onCancel: () => void;
  /** Tras crear: el layout selecciona el expediente nuevo. */
  onCreado: (expedienteId: number) => void;
};

/**
 * Alta del expediente (plan §3: nace con el comprobante de pago). Usa el
 * armazón común de `@features/expedientes`; los campos son propios.
 */
export default function NuevoExpediente({ catalogos, setToast, onCancel, onCreado }: Props) {
  const [form, setFormState] = useState<ExpedienteFormState>(FORM_VACIO);
  const [error, setError] = useState<string | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);
  const crear = useCrearExpedienteMutation();

  const setForm = (cambio: Partial<ExpedienteFormState>) => setFormState((prev) => ({ ...prev, ...cambio }));

  const cerrar = () => {
    setFormState(FORM_VACIO);
    setError(null);
    crear.reset();
    onCancel();
  };

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const invalido = validarExpedienteForm(form);
    if (invalido) {
      setError(invalido);
      return;
    }
    setError(null);
    crear.mutate(form, {
      onSuccess: (res) => {
        setToast({ id: Date.now(), message: res.message ?? "Expediente creado", type: "success" });
        setFormState(FORM_VACIO);
        onCreado(res.data.id);
        onCancel();
      },
      onError: (err) => setError(mensajeError(err, err instanceof Error ? err.message : "Error al crear el expediente")),
    });
  };

  return (
    <NuevoExpedienteLayout
      formId="nuevo-expediente-recurso"
      formRef={formRef}
      onSubmit={handleSubmit}
      onCancelar={cerrar}
      isSubmitting={crear.isPending}
      errorGeneral={error}
    >
      <ExpedienteFields form={form} setForm={setForm} catalogos={catalogos} disabled={crear.isPending} />
    </NuevoExpedienteLayout>
  );
}
