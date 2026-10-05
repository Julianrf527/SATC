import { useState } from "react";
import type { TipoCambio, TipoOperacion } from "../types";

export type ConfirmacionState = {
  isOpen: boolean;
  typeOperation: TipoOperacion;
  typeChange?: TipoCambio;
  itemIdentifier?: number | string;
  onConfirm: () => void;
};

const CERRADO: ConfirmacionState = {
  isOpen: false,
  typeOperation: "crear",
  onConfirm: () => {},
};

/** Estado del `ConfirmationModal` compartido por los formularios de roles y permisos. */
export function useConfirmacion() {
  const [confirmacion, setConfirmacion] = useState<ConfirmacionState>(CERRADO);

  const pedirConfirmacion = (
    typeOperation: TipoOperacion,
    typeChange: TipoCambio,
    itemIdentifier: number | string,
    onConfirm: () => void,
  ) => setConfirmacion({ isOpen: true, typeOperation, typeChange, itemIdentifier, onConfirm });

  const cerrarConfirmacion = () => setConfirmacion(CERRADO);

  return { confirmacion, pedirConfirmacion, cerrarConfirmacion };
}
