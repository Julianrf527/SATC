type Props = {
  /** Trazo SVG (viewBox 24x24). Ver `ICONOS`. */
  d: string;
  className?: string;
  strokeWidth?: number;
};

/** Icono de trazo (stroke) 24x24, el estilo de todos los iconos del módulo. */
export default function Icono({ d, className = "w-4 h-4", strokeWidth = 2 }: Props) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={strokeWidth} d={d} />
    </svg>
  );
}
