type Option = { value: number; label: string };

type Props = {
  value: number;
  onChange: (value: number) => void;
  options: Option[];
  placeholder?: string;
  /** Oculta el ítem "placeholder" de la lista — para campos que siempre tienen un valor válido. */
  hidePlaceholderOption?: boolean;
  disabled?: boolean;
  error?: boolean;
  className?: string;
};

/**
 * Listbox con el patrón `.dropdown` de daisyUI (foco/CSS, sin popover nativo)
 * en vez de <select>. El popup nativo de <select> parpadea en negro dentro de
 * modales con fondo translúcido/blur — ver NotificationModal. El dropdown de
 * perfil del header usa este mismo patrón y no tiene ese problema.
 */
export default function CustomSelect({
  value,
  onChange,
  options,
  placeholder = "",
  hidePlaceholderOption = false,
  disabled,
  error,
  className = "",
}: Props) {
  const selected = options.find((o) => o.value === value);

  const pick = (v: number) => {
    onChange(v);
    (document.activeElement as HTMLElement | null)?.blur();
  };

  return (
    <div
      className={`dropdown w-full [&_*]:!transition-none [&_*]:!animate-none ${disabled ? "pointer-events-none" : ""}`}
    >
      <div
        tabIndex={disabled ? -1 : 0}
        role="button"
        className={`select select-bordered w-full flex items-center justify-between gap-2 ${
          error ? "select-error" : "focus:select-success"
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""} ${className}`}
      >
        <span className={`truncate ${selected ? "" : "text-base-content/50"}`}>
          {selected ? selected.label : placeholder}
        </span>
        <svg
          className="w-4 h-4 flex-shrink-0"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>

      <ul
        tabIndex={0}
        className="dropdown-content menu bg-base-100 rounded-box z-[1] w-full max-h-60 overflow-y-auto p-2 shadow-lg border border-base-300 [transition:none!important] [animation:none!important]"
      >
        {!hidePlaceholderOption && (
          <li>
            <a
              onClick={() => pick(0)}
              className="text-base-content/50 hover:!bg-success/15 focus:!bg-success/15 active:!bg-success/25"
            >
              {placeholder}
            </a>
          </li>
        )}
        {options.map((opt) => (
          <li key={opt.value}>
            <a
              onClick={() => pick(opt.value)}
              className={`hover:!bg-success/15 focus:!bg-success/15 active:!bg-success/25 ${
                opt.value === value ? "bg-success/10 text-success font-medium" : ""
              }`}
            >
              {opt.label}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
