import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

type Props = {
  value: string; // yyyy-mm-dd
  onChange: (value: string) => void;
  max?: string; // yyyy-mm-dd
  placeholder?: string;
  disabled?: boolean;
  error?: boolean;
  className?: string;
};

const DIAS = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"];
const MESES = [
  "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
  "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
];

function parseYMD(s: string): Date | null {
  if (!s) return null;
  const [y, m, d] = s.split("-").map(Number);
  if (!y || !m || !d) return null;
  return new Date(y, m - 1, d);
}

function toYMD(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/**
 * Selector de fecha propio (sin <input type="date"> nativo) — el calendario
 * nativo del navegador parpadea en negro dentro de modales con fondo
 * translúcido/blur, ver NotificationModal.
 *
 * El popup se monta con un portal a document.body y se posiciona a mano en
 * vez de usar el patrón `.dropdown` de daisyUI: dentro de un modal con
 * `overflow-y-auto`, un popup absoluto sigue contando dentro del alto
 * scrolleable de ese contenedor y le agrega una scrollbar propia aunque
 * visualmente "flote" encima. Sacándolo del árbol del modal se evita eso.
 */
export default function CustomDateInput({
  value,
  onChange,
  max,
  placeholder = "Seleccionar fecha",
  disabled,
  error,
  className = "",
}: Props) {
  const selected = parseYMD(value);
  const maxDate = max ? parseYMD(max) : null;
  const [viewDate, setViewDate] = useState(() => selected || maxDate || new Date());
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<{ left: number; width: number; top?: number; bottom?: number }>({
    left: 0,
    width: 0,
  });
  const [theme, setTheme] = useState("emerald");
  const triggerRef = useRef<HTMLDivElement>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  const MAX_POPUP_HEIGHT = 300; // calendario completo (encabezado + 6 filas)

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
    // El popup se porta fuera del modal, así que ya no hereda su data-theme.
    setTheme(
      triggerRef.current?.closest("[data-theme]")?.getAttribute("data-theme") ||
        document.querySelector("[data-theme]")?.getAttribute("data-theme") ||
        "emerald",
    );
    setViewDate(selected || maxDate || new Date());
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

  const year = viewDate.getFullYear();
  const month = viewDate.getMonth();
  const firstDay = new Date(year, month, 1);
  const startOffset = (firstDay.getDay() + 6) % 7; // lunes primero
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (number | null)[] = [
    ...Array(startOffset).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  const isDisabledDay = (day: number) =>
    !!maxDate && new Date(year, month, day) > maxDate;

  const isSelectedDay = (day: number) =>
    !!selected &&
    selected.getFullYear() === year &&
    selected.getMonth() === month &&
    selected.getDate() === day;

  const isToday = (day: number) => {
    const today = new Date();
    return today.getFullYear() === year && today.getMonth() === month && today.getDate() === day;
  };

  const displayLabel = selected
    ? `${String(selected.getDate()).padStart(2, "0")}/${String(selected.getMonth() + 1).padStart(2, "0")}/${selected.getFullYear()}`
    : placeholder;

  const pick = (day: number) => {
    onChange(toYMD(new Date(year, month, day)));
    setOpen(false);
  };

  const clear = () => {
    onChange("");
    setOpen(false);
  };

  return (
    <>
      <div
        ref={triggerRef}
        tabIndex={disabled ? -1 : 0}
        role="button"
        onClick={openPopup}
        className={`input input-bordered w-full flex items-center justify-between gap-2 ${
          error ? "input-error" : "focus:input-success"
        } ${disabled ? "opacity-50 cursor-not-allowed" : ""} ${className}`}
      >
        <span className={selected ? "" : "text-base-content/50"}>{displayLabel}</span>
        <svg className="w-4 h-4 flex-shrink-0 text-base-content/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </div>

      {open &&
        createPortal(
          <div
            ref={popupRef}
            data-theme={theme}
            style={{ top: pos.top, bottom: pos.bottom, left: pos.left, minWidth: pos.width }}
            className="fixed z-[9999999] w-56 bg-base-100 rounded-box p-2 shadow-lg border border-base-300"
          >
            <div className="flex items-center justify-between mb-1">
              <button
                type="button"
                className="btn btn-ghost btn-xs px-1 hover:!bg-success/15 active:!bg-success/25"
                onClick={() => setViewDate(new Date(year, month - 1, 1))}
              >
                ‹
              </button>
              <span className="text-xs font-semibold">
                {MESES[month]} {year}
              </span>
              <button
                type="button"
                className="btn btn-ghost btn-xs px-1 hover:!bg-success/15 active:!bg-success/25"
                onClick={() => setViewDate(new Date(year, month + 1, 1))}
              >
                ›
              </button>
            </div>
            <div className="grid grid-cols-7 gap-0.5 text-center text-[10px] text-base-content/50 mb-0.5">
              {DIAS.map((d) => (
                <div key={d}>{d}</div>
              ))}
            </div>
            <div className="grid grid-cols-7 gap-0.5">
              {cells.map((day, i) =>
                day === null ? (
                  <div key={i} />
                ) : (
                  <button
                    key={i}
                    type="button"
                    disabled={isDisabledDay(day)}
                    onClick={() => pick(day)}
                    className={`text-xs rounded-md py-1 ${
                      isDisabledDay(day)
                        ? "text-base-content/20 cursor-not-allowed"
                        : isSelectedDay(day)
                          ? "bg-success text-white font-semibold"
                          : isToday(day)
                            ? "border border-success text-success hover:!bg-success/15 active:!bg-success/25"
                            : "hover:!bg-success/15 active:!bg-success/25"
                    }`}
                  >
                    {day}
                  </button>
                ),
              )}
            </div>
            {value && (
              <button
                type="button"
                className="btn btn-ghost btn-xs w-full mt-1 hover:!bg-success/15 active:!bg-success/25"
                onClick={clear}
              >
                Limpiar fecha
              </button>
            )}
          </div>,
          document.body,
        )}
    </>
  );
}
