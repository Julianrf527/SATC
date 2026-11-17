import {
  useEffect,
  useId,
  useRef,
  type ReactNode,
  type RefObject,
} from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import { useTheme } from "@shared/hooks/useTheme";
import { isTopModal, popModal, pushModal } from "./modalStack";

export type ModalSize = "sm" | "md" | "lg" | "xl" | "2xl" | "4xl" | "full";

const SIZE_CLASS: Record<ModalSize, string> = {
  sm: "max-w-sm",
  md: "max-w-md",
  lg: "max-w-lg",
  xl: "max-w-xl",
  "2xl": "max-w-2xl",
  "4xl": "max-w-4xl",
  full: "max-w-[95vw]",
};

export type ModalProps = {
  isOpen: boolean;
  onClose: () => void;
  /** Título del header. Si se omite, no se pinta header (usar `ariaLabel`). */
  title?: ReactNode;
  subtitle?: ReactNode;
  /** Slot del icono del header (p. ej. `<Upload size={20} />`). */
  icon?: ReactNode;
  /** Slot del footer (botones). Se alinea a la derecha. */
  footer?: ReactNode;
  children?: ReactNode;
  size?: ModalSize;
  /** Cerrar con Esc (por defecto true). Desactivar mientras se guarda. */
  closeOnEsc?: boolean;
  /** Cerrar al hacer clic en el fondo (por defecto true). */
  closeOnBackdrop?: boolean;
  /** Botón X del header (por defecto true). */
  showCloseButton?: boolean;
  /** Elemento que recibe el foco al abrir; si no, el primer enfocable. */
  initialFocusRef?: RefObject<HTMLElement | null>;
  /** Nombre accesible cuando no hay `title`. */
  ariaLabel?: string;
  /** Clases extra del panel / del body. */
  className?: string;
  bodyClassName?: string;
};

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Modal base: portal a `document.body` con el tema activo, `role="dialog"`,
 * cierre con Esc / fondo (configurable), foco inicial + trampa de Tab +
 * restauración del foco al cerrar, bloqueo de scroll del body y soporte de
 * modales anidados (Esc solo cierra el de arriba).
 *
 * Estilo: el mismo de los modales existentes (fondo `bg-black/50
 * backdrop-blur-sm`, panel `bg-base-100 rounded-lg shadow-2xl`, header con
 * borde inferior, footer con borde superior).
 */
export function Modal({
  isOpen,
  onClose,
  title,
  subtitle,
  icon,
  footer,
  children,
  size = "md",
  closeOnEsc = true,
  closeOnBackdrop = true,
  showCloseButton = true,
  initialFocusRef,
  ariaLabel,
  className = "",
  bodyClassName = "",
}: ModalProps) {
  const { theme } = useTheme();
  const panelRef = useRef<HTMLDivElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const modalId = useId();
  // Ref para no re-suscribir listeners cuando el padre pasa un onClose inline.
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  // Pila de modales + bloqueo de scroll + foco inicial/restauración.
  useEffect(() => {
    if (!isOpen) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    pushModal(modalId);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const target =
      initialFocusRef?.current ??
      // Primero el contenido (no la X del header), luego cualquier enfocable.
      bodyRef.current?.querySelector<HTMLElement>(FOCUSABLE) ??
      panelRef.current?.querySelector<HTMLElement>(FOCUSABLE) ??
      panelRef.current;
    // preventScroll: el panel es fijo y centrado; evita el scroll-into-view (layout extra).
    target?.focus({ preventScroll: true });

    return () => {
      popModal(modalId);
      document.body.style.overflow = prevOverflow;
      previouslyFocused?.focus?.({ preventScroll: true });
    };
  }, [isOpen, modalId, initialFocusRef]);

  // Esc + trampa de foco (solo el modal superior reacciona).
  useEffect(() => {
    if (!isOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (!isTopModal(modalId)) return;
      if (e.key === "Escape" && closeOnEsc) {
        e.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (e.key === "Tab" && panelRef.current) {
        const items = Array.from(panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE));
        if (items.length === 0) {
          e.preventDefault();
          return;
        }
        const first = items[0];
        const last = items[items.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [isOpen, modalId, closeOnEsc]);

  if (!isOpen) return null;

  const hasHeader = title !== undefined || icon !== undefined || showCloseButton;

  return createPortal(
    <div
      data-theme={theme}
      // Sin backdrop-blur: el desenfoque de pantalla completa (doble con modales
      // anidados) encarece cada cuadro en equipos modestos.
      className="fixed inset-0 z-[9999999] flex items-center justify-center bg-black/50 p-4"
      // mousedown (no click) para no cerrar si el usuario arrastra una selección hacia fuera.
      onMouseDown={(e) => {
        if (closeOnBackdrop && e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title !== undefined ? titleId : undefined}
        aria-label={title === undefined ? ariaLabel : undefined}
        tabIndex={-1}
        className={`bg-base-100 text-base-content rounded-lg w-full ${SIZE_CLASS[size]} max-h-[90vh] flex flex-col shadow-2xl border border-base-300 outline-none ${className}`}
      >
        {hasHeader && (
          <div className="border-b border-base-300 px-6 py-4 flex items-center justify-between gap-3 shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              {icon !== undefined && (
                <div className="w-10 h-10 bg-primary/10 text-primary rounded-lg flex items-center justify-center shrink-0">
                  {icon}
                </div>
              )}
              {title !== undefined && (
                <div className="min-w-0">
                  <h3 id={titleId} className="font-bold text-lg text-base-content truncate">
                    {title}
                  </h3>
                  {subtitle !== undefined && (
                    <p className="text-xs text-base-content/60">{subtitle}</p>
                  )}
                </div>
              )}
            </div>
            {showCloseButton && (
              <button
                type="button"
                onClick={onClose}
                className="btn btn-ghost btn-sm btn-circle"
                aria-label="Cerrar"
              >
                <X size={18} />
              </button>
            )}
          </div>
        )}

        <div ref={bodyRef} className={`px-6 py-4 overflow-y-auto flex-1 ${bodyClassName}`}>{children}</div>

        {footer !== undefined && (
          <div className="border-t border-base-300 px-6 py-3 flex justify-end gap-2 shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}

export default Modal;
