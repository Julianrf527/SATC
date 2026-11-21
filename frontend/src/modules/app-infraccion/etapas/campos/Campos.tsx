import { useId, type ReactNode } from "react";
import { FileText } from "lucide-react";
import { openDocumentById } from "@shared/lib/documentViewer";
import { Campo, CustomDateInput, CustomSelect } from "@shared/ui";

/*
 * Campos de los formularios en modal de infracciones, réplica de
 * `app-recurso/etapas/comun/campos/Campos.tsx`: `Campo` compartido, inputs de
 * tamaño normal a todo el ancho, fecha con `CustomDateInput` y opciones con
 * `CustomSelect`.
 */

const Requerido = () => <span className="text-error"> *</span>;

const hoy = () => new Date().toISOString().split("T")[0];

/** Recuadro con título en mayúsculas que agrupa campos (como en recurso). */
export function Seccion({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className="border border-base-300 rounded-lg p-3 space-y-3">
      <h4 className="text-xs font-semibold text-base-content/60 uppercase tracking-wider">{titulo}</h4>
      {children}
    </section>
  );
}

function VerActual({ fileId }: { fileId: number }) {
  return (
    <button
      type="button"
      onClick={() => openDocumentById(fileId)}
      className="btn btn-ghost btn-xs gap-1 text-success px-1"
      title="Ver actual"
    >
      <FileText size={14} />
      Ver actual
    </button>
  );
}

type ArchivoProps = {
  etiqueta: string;
  archivo: File | null;
  onChange: (archivo: File | null) => void;
  requerido?: boolean;
  /** Documento ya cargado (se reemplaza si se elige otro). */
  actualId?: number | null;
  disabled?: boolean;
};

/** Selector de PDF. */
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
      extra={actualId ? <VerActual fileId={actualId} /> : undefined}
      // El "(PDF)" va en la etiqueta: sin ayuda redundante bajo el campo.
      ayuda={archivo ? archivo.name : actualId ? "Deje vacío para mantener el actual" : undefined}
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
  /** Texto de ayuda bajo el campo (formato esperado...). */
  ayuda?: string;
  /** Mensaje de error del campo (borde rojo). */
  error?: string | null;
  disabled?: boolean;
};

export function CampoTexto({
  etiqueta,
  valor,
  onChange,
  requerido,
  maxLength,
  placeholder,
  inputMode,
  ayuda,
  error,
  disabled,
}: TextoProps) {
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
      ayuda={ayuda}
      error={error || undefined}
    >
      <input
        id={id}
        type="text"
        className={`input w-full ${error ? "input-error" : ""}`}
        value={valor}
        maxLength={maxLength}
        placeholder={placeholder}
        inputMode={inputMode}
        disabled={disabled}
        aria-invalid={!!error}
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
