import { CheckCircle2 } from "lucide-react";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { PersonaFormState } from "./usePersonaForm";

type Props = {
  titulo: string;
  persona: PersonaFormState;
  disabled: boolean;
};

const TIPOS = [
  { value: "CC", label: "Cédula (CC)" },
  { value: "NIT", label: "NIT" },
  { value: "CE", label: "Extranjería (CE)" },
  { value: "PP", label: "Pasaporte" },
];

/**
 * Campos de una persona (matriz 2x3 como el formulario de involucrados de
 * infraction). Se usa para el solicitante y su representante legal.
 */
export default function PersonaFields({ titulo, persona, disabled }: Props) {
  const { form, existente, buscando, setCampo, cambiarDocumento, buscar } = persona;
  const bloqueado = disabled || !!existente;

  return (
    <fieldset className="space-y-3">
      <legend className="text-xs font-semibold text-base-content/60 uppercase tracking-wider mb-1 flex items-center gap-2">
        {titulo}
        {existente && (
          <span className="inline-flex items-center gap-1 text-success normal-case tracking-normal font-medium">
            <CheckCircle2 size={14} /> Persona encontrada — solo se vinculará
          </span>
        )}
      </legend>
      <div className="grid grid-cols-3 gap-3">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Tipo documento *</span>
          <CustomSelect
            hidePlaceholderOption
            value={form.tipo_documento}
            onChange={(v) => cambiarDocumento({ tipo_documento: v, digito_verificacion: v === "NIT" ? form.digito_verificacion : "" })}
            disabled={disabled}
            options={TIPOS}
          />
        </div>

        <div className="col-span-2 flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60 flex items-center gap-1">
            Número de documento *
            {buscando && <span className="loading loading-spinner loading-xs" />}
          </span>
          <div className="flex gap-2">
            <input
              type="text"
              value={form.numero_documento}
              onChange={(e) => cambiarDocumento({ numero_documento: e.target.value.replace(/\D/g, "") })}
              onBlur={() => void buscar()}
              className="input flex-1 font-mono"
              disabled={disabled}
              placeholder="Ej: 1234567890"
              maxLength={15}
            />
            {form.tipo_documento === "NIT" && (
              <input
                type="text"
                value={form.digito_verificacion}
                onChange={(e) => cambiarDocumento({ digito_verificacion: e.target.value.replace(/\D/g, "").slice(0, 2) })}
                onBlur={() => void buscar()}
                className="input w-20 text-center font-mono"
                disabled={disabled}
                placeholder="DV"
                aria-label="Dígito de verificación"
              />
            )}
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Nombre completo *</span>
          <input
            type="text"
            value={form.nombre}
            onChange={(e) => setCampo("nombre", e.target.value)}
            className="input w-full"
            disabled={bloqueado}
            placeholder="Nombre completo"
            maxLength={100}
          />
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Celular</span>
          <input
            type="text"
            value={form.celular}
            onChange={(e) => setCampo("celular", e.target.value.replace(/\D/g, ""))}
            className="input w-full font-mono"
            disabled={bloqueado}
            placeholder="3001234567"
            maxLength={15}
          />
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Correo</span>
          <input
            type="email"
            value={form.correo}
            onChange={(e) => setCampo("correo", e.target.value)}
            className="input w-full"
            disabled={bloqueado}
            placeholder="ejemplo@correo.com"
            maxLength={100}
          />
        </div>
        <div className="col-span-3 flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Dirección</span>
          <input
            type="text"
            value={form.direccion}
            onChange={(e) => setCampo("direccion", e.target.value)}
            className="input w-full"
            disabled={bloqueado}
            placeholder="Dirección de residencia o notificación"
            maxLength={200}
          />
        </div>
      </div>
    </fieldset>
  );
}
