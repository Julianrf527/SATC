import type { FormEvent } from "react";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { TipoMedida } from "../../types";

const ESTADO_OPTIONS = [
  { value: "true", label: "Vigente" },
  { value: "false", label: "Levantada" },
  { value: "null", label: "No aplica" },
];

const UNIDADES_OPTIONS = [
  { value: "m³", label: "m³" },
  { value: "L", label: "Litros" },
  { value: "m²", label: "m²" },
  { value: "Ha", label: "Hectáreas" },
  { value: "kg", label: "Kilogramos" },
  { value: "ton", label: "Toneladas" },
  { value: "und", label: "Unidades" },
  { value: "m", label: "Metros" },
  { value: "km", label: "Kilómetros" },
];

export type MedidaFormValues = {
  tipoMedidaId: number;
  cantidadValor: string;
  cantidadUnidad: string;
  especie: string;
  /** "true" | "false" | "null" (valor del select de estado). */
  estadoMedida: string;
};

type Props = {
  values: MedidaFormValues;
  onChange: (patch: Partial<MedidaFormValues>) => void;
  tipoMedidas: TipoMedida[];
  isSubmitting: boolean;
  onSubmit: (e: FormEvent) => void;
  /** Solo en edición: muestra "Cancelar" y el texto "Actualizar medida". */
  onCancel?: () => void;
};

/**
 * Formulario de la medida preventiva. Antes había dos copias casi idénticas
 * (crear y editar); solo difieren en el botón Cancelar y el texto del submit.
 */
export default function MedidaPreventivaForm({
  values,
  onChange,
  tipoMedidas,
  isSubmitting,
  onSubmit,
  onCancel,
}: Props) {
  const esEdicion = !!onCancel;
  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="flex flex-col md:col-span-2">
          <label className="label">
            <span className="text-sm text-base-content font-medium">Tipo de Medida *</span>
          </label>
          <CustomSelect
            value={values.tipoMedidaId || 0}
            onChange={(v) => onChange({ tipoMedidaId: v })}
            placeholder="Seleccione un tipo"
            disabled={isSubmitting}
            options={tipoMedidas.map((t) => ({ value: t.id, label: t.nombre }))}
          />
        </div>

        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">Cantidad *</span>
          </label>
          <div className="flex gap-2">
            <input
              type="number"
              className="input w-2/3"
              value={values.cantidadValor}
              onChange={(e) => onChange({ cantidadValor: e.target.value })}
              disabled={isSubmitting}
              placeholder="0"
              step="0.01"
              min="0"
              required
            />
            <CustomSelect
              className="w-1/3"
              value={values.cantidadUnidad}
              onChange={(v) => onChange({ cantidadUnidad: v })}
              emptyValue=""
              placeholder="Unidad"
              disabled={isSubmitting}
              options={UNIDADES_OPTIONS}
            />
          </div>
        </div>

        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">Especie *</span>
          </label>
          <input
            type="text"
            className="input w-full"
            value={values.especie}
            onChange={(e) => onChange({ especie: e.target.value })}
            disabled={isSubmitting}
            placeholder="Ej: Bovinos"
            maxLength={200}
          />
        </div>

        <div className="flex flex-col">
          <label className="label">
            <span className="text-sm text-base-content font-medium">Estado de la Medida</span>
          </label>
          <CustomSelect
            hidePlaceholderOption
            value={values.estadoMedida}
            onChange={(v) => onChange({ estadoMedida: v })}
            options={ESTADO_OPTIONS}
          />
        </div>
      </div>

      <div className="flex gap-3 justify-end pt-2 border-t border-base-300">
        {esEdicion && (
          <button type="button" className="btn btn-outline" onClick={onCancel} disabled={isSubmitting}>
            Cancelar
          </button>
        )}
        <button type="submit" className="btn btn-info text-white" disabled={isSubmitting}>
          {isSubmitting ? (
            <>
              <span className="loading loading-spinner loading-sm" />
              Guardando...
            </>
          ) : esEdicion ? (
            "Actualizar medida"
          ) : (
            "Registrar medida"
          )}
        </button>
      </div>
    </form>
  );
}
