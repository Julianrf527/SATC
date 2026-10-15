import { useId } from "react";
import { Campo, CustomDateInput, CustomSelect } from "@shared/ui";
import { VerDocumento } from "../Dato";
import { hoy } from "../../formularios/comunes";

const Requerido = () => <span className="text-error"> *</span>;

type ArchivoProps = {
  etiqueta: string;
  archivo: File | null;
  onChange: (archivo: File | null) => void;
  requerido?: boolean;
  /** Documento ya cargado (se reemplaza si se elige otro). */
  actualId?: number | null;
  disabled?: boolean;
};

/** Selector de PDF (todo documento de etapa es PDF). */
export function CampoPdf({ etiqueta, archivo, onChange, requerido, actualId, disabled }: ArchivoProps) {
  const id = useId();
  return (
    <Campo
      etiqueta={
        <>
          {etiqueta}
          {requerido && <Requerido />}
        </>
      }
      htmlFor={id}
      extra={actualId ? <VerDocumento fileId={actualId} texto="Ver actual" /> : undefined}
      ayuda={archivo ? archivo.name : actualId ? "Deje vacío para mantener el actual" : "Solo PDF"}
    >
      <input
        id={id}
        type="file"
        accept=".pdf,application/pdf"
        className="file-input w-full"
        disabled={disabled}
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
    </Campo>
  );
}

type FechaProps = {
  etiqueta: string;
  valor: string;
  onChange: (v: string) => void;
  requerido?: boolean;
  /** Por defecto no se permiten fechas futuras. */
  permitirFutura?: boolean;
  disabled?: boolean;
};

export function CampoFecha({ etiqueta, valor, onChange, requerido, permitirFutura, disabled }: FechaProps) {
  return (
    <Campo
      etiqueta={
        <>
          {etiqueta}
          {requerido && <Requerido />}
        </>
      }
    >
      <CustomDateInput value={valor} onChange={onChange} max={permitirFutura ? undefined : hoy()} disabled={disabled} />
    </Campo>
  );
}

type TextoProps = {
  etiqueta: string;
  valor: string;
  onChange: (v: string) => void;
  requerido?: boolean;
  maxLength?: number;
  placeholder?: string;
  inputMode?: "text" | "numeric" | "decimal";
  disabled?: boolean;
};

export function CampoTexto({ etiqueta, valor, onChange, requerido, maxLength, placeholder, inputMode, disabled }: TextoProps) {
  const id = useId();
  return (
    <Campo
      etiqueta={
        <>
          {etiqueta}
          {requerido && <Requerido />}
        </>
      }
      htmlFor={id}
    >
      <input
        id={id}
        type="text"
        className="input w-full"
        value={valor}
        maxLength={maxLength}
        placeholder={placeholder}
        inputMode={inputMode}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
    </Campo>
  );
}

type OpcionesProps<T extends string | number> = {
  etiqueta: string;
  valor: T | "";
  opciones: { value: T; label: string }[];
  onChange: (v: T | "") => void;
  requerido?: boolean;
  placeholder?: string;
  disabled?: boolean;
};

export function CampoOpciones<T extends string | number>({
  etiqueta,
  valor,
  opciones,
  onChange,
  requerido,
  placeholder = "Seleccione...",
  disabled,
}: OpcionesProps<T>) {
  return (
    <Campo
      etiqueta={
        <>
          {etiqueta}
          {requerido && <Requerido />}
        </>
      }
    >
      <CustomSelect<T | "">
        value={valor}
        onChange={onChange}
        options={opciones}
        placeholder={placeholder}
        emptyValue=""
        disabled={disabled}
      />
    </Campo>
  );
}

type SiNoProps = {
  etiqueta: string;
  valor: boolean | null;
  onChange: (v: boolean) => void;
  si?: string;
  no?: string;
  requerido?: boolean;
  disabled?: boolean;
};

/** Sí / No con botones (cumple, requiere memorias). */
export function CampoSiNo({ etiqueta, valor, onChange, si = "Sí", no = "No", requerido, disabled }: SiNoProps) {
  return (
    <Campo
      etiqueta={
        <>
          {etiqueta}
          {requerido && <Requerido />}
        </>
      }
    >
      <div className="flex gap-2" role="radiogroup" aria-label={etiqueta}>
        {[
          { v: true, label: si, clase: "btn-success" },
          { v: false, label: no, clase: "btn-error" },
        ].map((o) => (
          <button
            key={o.label}
            type="button"
            role="radio"
            aria-checked={valor === o.v}
            disabled={disabled}
            className={`btn btn-sm flex-1 ${valor === o.v ? `${o.clase} text-white` : "btn-outline"}`}
            onClick={() => onChange(o.v)}
          >
            {o.label}
          </button>
        ))}
      </div>
    </Campo>
  );
}
