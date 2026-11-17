import type React from "react";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { InvolucradoFormState } from "./useInvolucradoForm";

type Props = {
  form: InvolucradoFormState;
  isLoading: boolean;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
};

/** Formulario de alta/vinculación de un involucrado (matriz 2x3). */
export default function InvolucradoFormView({ form, isLoading, onSubmit, onCancel }: Props) {
  const { formData, existingInvolucrado, setField, handleDocumentChange, handleTipoChange, triggerSearch } = form;

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      {/* Matriz 2×3 */}
      <div className="grid grid-cols-3 gap-3">
        {/* [1.1] Tipo */}
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Tipo documento *</span>
          <CustomSelect
            hidePlaceholderOption
            value={formData.tipo_documento}
            onChange={handleTipoChange}
            disabled={isLoading}
            options={[
              { value: "CC", label: "Cédula (CC)" },
              { value: "NIT", label: "NIT" },
              { value: "CE", label: "Extranjería (CE)" },
              { value: "PP", label: "Pasaporte" },
            ]}
          />
        </div>

        {/* [1.2 + 1.3] Número (ocupa 2 columnas) */}
        <div className="col-span-2 flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60 flex items-center gap-1">
            Número de documento *
            {isLoading && <span className="loading loading-spinner loading-xs" />}
          </span>
          <div className="flex gap-2">
            <input
              type="text"
              value={formData.numero_documento}
              onChange={(e) => handleDocumentChange(e.target.value)}
              onBlur={triggerSearch}
              className="input flex-1 font-mono"
              required disabled={isLoading}
              placeholder="Ej: 1234567890"
              minLength={7} maxLength={15}
            />
            {formData.tipo_documento === "NIT" && (
              <input
                type="text"
                value={formData.digito_verificacion}
                onChange={(e) => setField("digito_verificacion", e.target.value.replace(/\D/g, "").slice(0, 2))}
                onBlur={triggerSearch}
                className="input w-20 text-center font-mono"
                required disabled={isLoading}
                placeholder="DV"
              />
            )}
          </div>
        </div>

        {/* [2.1] Nombre */}
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Nombre completo *</span>
          <input
            type="text"
            value={formData.nombre}
            onChange={(e) => setField("nombre", e.target.value)}
            className="input w-full"
            required disabled={isLoading || !!existingInvolucrado}
            placeholder="Nombre completo"
            maxLength={100}
          />
        </div>

        {/* [2.2] Celular */}
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Celular</span>
          <input
            type="text"
            value={formData.celular}
            onChange={(e) => setField("celular", e.target.value.replace(/\D/g, ""))}
            className="input w-full font-mono"
            disabled={isLoading || !!existingInvolucrado}
            placeholder="3001234567"
            maxLength={15}
          />
        </div>

        {/* [2.3] Correo */}
        <div className="flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Correo</span>
          <input
            type="email"
            value={formData.correo}
            onChange={(e) => setField("correo", e.target.value)}
            className="input w-full"
            disabled={isLoading || !!existingInvolucrado}
            placeholder="ejemplo@correo.com"
            maxLength={100}
          />
        </div>

        {/* [3.1-3.3] Dirección (ocupa toda la fila) */}
        <div className="col-span-3 flex flex-col gap-1">
          <span className="text-xs font-medium text-base-content/60">Dirección</span>
          <input
            type="text"
            value={formData.direccion}
            onChange={(e) => setField("direccion", e.target.value)}
            className="input w-full"
            disabled={isLoading || !!existingInvolucrado}
            placeholder="Dirección de residencia o notificación"
            maxLength={200}
          />
        </div>
      </div>

      {/* Botones */}
      <div className="flex items-center gap-2 pt-2 border-t border-base-300">
        {existingInvolucrado && (
          <div className="flex items-center gap-1.5 text-success text-xs flex-1">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Involucrado encontrado — solo se vinculará al expediente</span>
          </div>
        )}
        <div className="flex gap-2 ml-auto">
        <button type="button" onClick={onCancel} className="btn btn-ghost btn-sm" disabled={isLoading}>
          Cancelar
        </button>
        <button type="submit" className="btn btn-warning btn-sm text-white gap-1.5" disabled={isLoading}>
          {isLoading ? (
            <><span className="loading loading-spinner loading-xs" />
              {existingInvolucrado ? "Vinculando..." : "Creando..."}</>
          ) : (
            <><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              {existingInvolucrado ? "Vincular" : "Crear y Vincular"}</>
          )}
        </button>
        </div>
      </div>
    </form>
  );
}
