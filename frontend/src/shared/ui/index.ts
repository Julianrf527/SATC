// Barrel de componentes UI compartidos: `import { Modal, EstadoBadge } from "@shared/ui"`.
// Solo componentes sin conocimiento de dominio (expedientes, etapas, flujos...).
export { Modal, type ModalProps, type ModalSize } from "./modal/Modal";
export {
  EstadoBadge,
  type EstadoBadgeProps,
  type EstadoTono,
  type EstadoVisual,
} from "./estado-badge/EstadoBadge";
export { default as ErrorBoundary } from "./ErrorBoundary";
export { default as LoadingBar } from "./LoadingBar";
export { default as Toast } from "./Toast";
export { default as CustomSelect } from "./form/CustomSelect";
export { default as CustomDateInput } from "./form/CustomDateInput";
export { Campo, Label } from "./form/Campo";
