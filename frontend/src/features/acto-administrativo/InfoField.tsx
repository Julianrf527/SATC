import type { ReactNode } from "react";

export type InfoFieldTone = "success" | "warning" | "info" | "primary";

// Clases completas (no interpoladas) para que Tailwind las detecte.
const TONE_CLASS: Record<InfoFieldTone, string> = {
  success: "bg-success/10 text-success",
  warning: "bg-warning/10 text-tono-warning",
  info: "bg-info/10 text-tono-info",
  primary: "bg-primary/10 text-primary",
};

type Props = {
  /** Atributo `d` del path del icono (heroicons outline 24x24). */
  iconPath: string;
  tone: InfoFieldTone;
  label: string;
  children: ReactNode;
  valueClassName?: string;
};

/** Dato con icono circular + etiqueta pequeña + valor (tarjetas de notificación/comunicación). */
export default function InfoField({
  iconPath,
  tone,
  label,
  children,
  valueClassName = "text-sm font-semibold",
}: Props) {
  return (
    <div className="flex items-start gap-3 min-w-0">
      <div
        className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${TONE_CLASS[tone]}`}
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d={iconPath}
          />
        </svg>
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-base-content/60 font-medium mb-1">{label}</p>
        <p className={valueClassName}>{children}</p>
      </div>
    </div>
  );
}
