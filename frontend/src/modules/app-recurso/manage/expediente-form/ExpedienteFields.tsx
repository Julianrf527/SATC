import type { ReactNode } from "react";
import { Campo } from "@shared/ui/form/Campo";
import CustomDateInput from "@shared/ui/form/CustomDateInput";
import CustomSelect from "@shared/ui/form/CustomSelect";
import type { CatalogosRecurso } from "../../types";
import ComprobantePagoField from "./ComprobantePagoField";
import SeleccionMultiple from "./SeleccionMultiple";
import {
  alternar,
  MAX_LONGITUD,
  type CampoTextoExpediente,
  type ExpedienteFormState,
} from "./expedienteForm";

type Props = {
  form: ExpedienteFormState;
  setForm: (cambio: Partial<ExpedienteFormState>) => void;
  catalogos: CatalogosRecurso;
  disabled?: boolean;
  /** Clases de la grilla: una columna en la lista lateral, dos en el detalle. */
  columnas?: string;
};

const hoy = () => new Date().toISOString().split("T")[0];

/** Título de sección dentro del formulario. */
function Seccion({ titulo, children, columnas }: { titulo: string; children: ReactNode; columnas: string }) {
  return (
    <fieldset className="space-y-3">
      <legend className="text-xs font-semibold text-base-content/60 uppercase tracking-wider mb-2">{titulo}</legend>
      <div className={columnas}>{children}</div>
    </fieldset>
  );
}

/**
 * Campos de la información base (plan §3), comunes al alta (lista lateral) y
 * a la edición (pestaña Información base). Solo forma: las reglas de
 * negocio las valida el backend.
 */
export default function ExpedienteFields({
  form,
  setForm,
  catalogos,
  disabled = false,
  columnas = "grid grid-cols-1 gap-4",
}: Props) {
  const texto = (campo: CampoTextoExpediente, etiqueta: string, placeholder: string) => (
    <Campo etiqueta={`${etiqueta} *`}>
      <input
        type="text"
        className="input w-full"
        value={form[campo]}
        onChange={(e) => setForm({ [campo]: e.target.value } as Partial<ExpedienteFormState>)}
        placeholder={placeholder}
        maxLength={MAX_LONGITUD[campo]}
        required
        disabled={disabled}
      />
    </Campo>
  );

  const fecha = (campo: "fecha_radicado" | "fecha_oficio_entrada", etiqueta: string) => (
    <Campo etiqueta={`${etiqueta} *`}>
      <CustomDateInput value={form[campo]} onChange={(v) => setForm({ [campo]: v } as Partial<ExpedienteFormState>)} max={hoy()} disabled={disabled} />
    </Campo>
  );

  const municipio = catalogos.municipios.find((m) => m.id === form.municipio_id);
  const veredas = municipio?.veredas ?? [];

  return (
    <div className="space-y-6">
      <Seccion titulo="Radicación" columnas={columnas}>
        {texto("radicado", "Radicado", "Ej: 2026ER00012")}
        {fecha("fecha_radicado", "Fecha de radicado")}
        {texto("expediente", "Expediente", "Ej: CA 001-26")}
        {texto("numero_vital", "Número VITAL", "Número VITAL")}
        {texto("radicado_oficio_entrada", "Radicado de la solicitud", "Radicado del oficio de entrada")}
        {fecha("fecha_oficio_entrada", "Fecha de la solicitud")}
      </Seccion>

      <ComprobantePagoField
        archivo={form.comprobante}
        onChange={(comprobante) => setForm({ comprobante })}
        fileIdActual={form.doc_comprobante_pago_id}
        disabled={disabled}
      />

      <Seccion titulo="Predio" columnas={columnas}>
        {texto("nombre_predio", "Nombre del predio", "Nombre del predio")}
        {texto("matricula_inmobiliaria", "Matrícula inmobiliaria", "Ej: 078-12345")}
        {texto("codigo_catastral", "Código catastral", "Código catastral")}
        <Campo etiqueta="Municipio *">
          <CustomSelect
            value={form.municipio_id}
            onChange={(id) => setForm({ municipio_id: id, vereda_id: 0 })}
            placeholder="Seleccione un municipio"
            disabled={disabled}
            options={catalogos.municipios.map((m) => ({ value: m.id, label: m.nombre }))}
          />
        </Campo>
        <Campo etiqueta="Vereda *">
          <CustomSelect
            value={form.vereda_id}
            onChange={(id) => setForm({ vereda_id: id })}
            placeholder={veredas.length === 0 ? "Seleccione primero un municipio" : "Seleccione una vereda"}
            disabled={disabled || veredas.length === 0}
            options={veredas.map((v) => ({ value: v.id, label: v.nombre }))}
          />
        </Campo>
      </Seccion>

      <Seccion titulo="Fuente y usos del agua" columnas={columnas}>
        <Campo etiqueta="Tipo de fuente *">
          <CustomSelect
            value={form.tipo_fuente_id}
            onChange={(id) => setForm({ tipo_fuente_id: id })}
            placeholder="Seleccione el tipo de fuente"
            disabled={disabled}
            options={catalogos.tipos_fuente.map((t) => ({ value: t.id, label: t.nombre }))}
          />
        </Campo>
        {texto("nombre_fuente", "Nombre de la fuente", "Ej: Juancho Castro")}
        <SeleccionMultiple
          etiqueta="Fuentes *"
          opciones={catalogos.fuentes.map((f) => ({ value: f.id, label: f.nombre }))}
          seleccionados={form.fuente_ids}
          onToggle={(id) => setForm({ fuente_ids: alternar(form.fuente_ids, id) })}
          disabled={disabled}
        />
        <SeleccionMultiple
          etiqueta="Usos del agua *"
          opciones={catalogos.usos.map((u) => ({ value: u, label: u }))}
          seleccionados={form.usos}
          onToggle={(u) => setForm({ usos: alternar(form.usos, u) })}
          disabled={disabled}
        />
      </Seccion>
    </div>
  );
}
