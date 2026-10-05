import type { LabelHTMLAttributes, ReactNode } from "react";

type LabelProps = LabelHTMLAttributes<HTMLLabelElement> & {
  /** Texto secundario alineado a la derecha (contador, "opcional"...). */
  extra?: ReactNode;
};

/**
 * Título de un campo de formulario, legible en claro y oscuro.
 *
 * Reemplaza el patrón de daisyUI 4 `<label class="label"><span
 * class="label-text">`: en daisyUI 5 `label-text` ya no existe y `.label`
 * pinta el texto al 60 % de `currentColor`, así que el título quedaba
 * desteñido. Aquí el color sale siempre del token del tema
 * (`text-base-content`), sin depender del color heredado.
 */
export function Label({ extra, className = "", children, ...rest }: LabelProps) {
  return (
    <label
      className={`flex items-center justify-between gap-2 mb-1 text-sm font-medium text-base-content ${className}`}
      {...rest}
    >
      <span>{children}</span>
      {extra && <span className="text-xs font-normal text-base-content/70">{extra}</span>}
    </label>
  );
}

type CampoProps = {
  /** Título del campo (se omite el <label> si no se pasa). */
  etiqueta?: ReactNode;
  /** id del control, para enlazar el <label>. */
  htmlFor?: string;
  /** Texto secundario a la derecha del título. */
  extra?: ReactNode;
  /** Ayuda bajo el control (se oculta si hay `error`). */
  ayuda?: ReactNode;
  /** Mensaje de error bajo el control. */
  error?: ReactNode;
  className?: string;
  children: ReactNode;
};

/**
 * Grupo título + control + ayuda/error. Equivale al `form-control` de
 * daisyUI 4 (eliminado en la v5) usando solo tokens del tema.
 *
 *   <Campo etiqueta="Dirección *" ayuda="Máximo 100 caracteres">
 *     <input className="input w-full" ... />
 *   </Campo>
 */
export function Campo({ etiqueta, htmlFor, extra, ayuda, error, className = "", children }: CampoProps) {
  const pie = error || ayuda;
  return (
    <div className={`flex flex-col ${className}`}>
      {etiqueta && (
        <Label htmlFor={htmlFor} extra={extra}>
          {etiqueta}
        </Label>
      )}
      {children}
      {pie && (
        <p className={`mt-1 px-1 text-xs ${error ? "text-error" : "text-base-content/70"}`}>{pie}</p>
      )}
    </div>
  );
}
