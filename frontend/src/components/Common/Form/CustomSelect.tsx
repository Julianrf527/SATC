import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

type Option<T> = { value: T; label: string };

type Props<T> = {
  value: T;
  onChange: (value: T) => void;
  options: Option<T>[];
  placeholder?: string;
  /** Oculta el ítem "placeholder" de la lista — para campos que siempre tienen un valor válido. */
  hidePlaceholderOption?: boolean;
  /** Valor que se envía a onChange al hacer click en el ítem "placeholder" (limpiar selección). */
  emptyValue?: T;
  disabled?: boolean;
  error?: boolean;
  className?: string;
};

/**
 * Listbox propio (sin <select> nativo) — el popup nativo de <select> parpadea
 * en negro dentro de modales con fondo translúcido/blur, ver
 * NotificationModal.
 *
 * El popup se monta con un portal a document.body y se posiciona a mano en
 * vez de usar el patrón `.dropdown` de daisyUI: dentro de un modal con
 * `overflow-y-auto`, un popup absoluto sigue contando dentro del alto
 * scrolleable de ese contenedor y le agrega una scrollbar propia aunque
 * visualmente "flote" encima. Sacándolo del árbol del modal se evita eso.
 */
export default function CustomSelect<T extends string | number>({
  value,
  onChange,
  options,
  placeholder = "",
  hidePlaceholderOption = false,
  emptyValue,
  disabled,
  error,
  className = "",
}: Props<T>) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ left: number; width: number; top?: number; bottom?: number }>({
    left: 0,
    width: 0,
  });
  const [theme, setTheme] = useState("emerald");
  const triggerRef = useRef<HTMLDivElement>(null);
  const popupRef = useRef<HTMLUListElement>(null);

  const selected = options.find((o) => o.value === value);

  const MAX_POPUP_HEIGHT = 240; // max-h-60

  const openPopup = () => {
    if (disabled) return;
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) {
      const spaceBelow = window.innerHeight - rect.bottom;
      const spaceAbove = rect.top;
      const openUpward = spaceBelow < MAX_POPUP_HEIGHT && spaceAbove > spaceBelow;
      setPos(
        openUpward
          ? { bottom: window.innerHeight - rect.top + 4, left: rect.left, width: rect.width }
          : { top: rect.bottom + 4, left: rect.left, width: rect.width },
      );
    }
    setTheme(
      triggerRef.current?.closest("[data-theme]")?.getAttribute("data-theme") ||
        document.querySelector("[data-theme]")?.getAttribute("data-theme") ||
        "emerald",
    );
    setOpen(true);
  };

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        !triggerRef.current?.contains(target) &&
        !popupRef.current?.contains(target)
      ) {
        setOpen(false);
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [open]);

  const pick = (v: T) => {
    onChange(v);
    setOpen(false);
  };

  return (
    <>
      <div
        ref={triggerRef}
        tabIndex={disabled ? -1 : 0}
        role="button"
        onClick={openPopup}
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

      {open &&
        createPortal(
          <ul
            ref={popupRef}
            data-theme={theme}
            style={{ top: pos.top, bottom: pos.bottom, left: pos.left, width: pos.width }}
            className="fixed z-[9999999] flex flex-col bg-base-100 rounded-box max-h-60 overflow-y-auto p-2 shadow-lg border border-base-300"
          >
            {!hidePlaceholderOption && (
              <li>
                <a
                  onClick={() => pick((emptyValue ?? (0 as unknown)) as T)}
                  className="block w-full text-left px-3 py-2 rounded-lg text-sm text-base-content/50 hover:!bg-success/15 focus:!bg-success/15 active:!bg-success/25"
                >
                  {placeholder}
                </a>
              </li>
            )}
            {options.map((opt) => (
              <li key={opt.value}>
                <a
                  onClick={() => pick(opt.value)}
                  className={`block w-full text-left px-3 py-2 rounded-lg text-sm hover:!bg-success/15 focus:!bg-success/15 active:!bg-success/25 ${
                    opt.value === value ? "bg-success/10 text-success font-medium" : ""
                  }`}
                >
                  {opt.label}
                </a>
              </li>
            ))}
          </ul>,
          document.body,
        )}
    </>
  );
}
