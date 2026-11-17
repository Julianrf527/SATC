import { useAuth } from "@shared/context/AuthContext";
import type { Municipio, ModeloGenerico } from "@shared/types/common";
import type { Expediente } from "@shared/types/sancionatorio";
import { ExpedienteList as ExpedienteListBase, type SetToast } from "@features/expedientes";
import NuevoExpediente from "./NuevoExpediente";
import {
  expedientesSancionatorioAdapter,
  expedientesSancionatorioConfig,
} from "./expedientesAdapter";

type Props = {
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  setToast: SetToast;
  setExpedienteSeleccionado: (expediente: Expediente | null) => void;
  expedienteList: Expediente[];
  /** Tras crear un expediente (p. ej. invalidar el listado). */
  onExpedienteCreado?: (expediente: Expediente) => void;
  isEditable?: boolean;
};

/** Monta la lista compartida de `@features/expedientes` con el adapter de sancionatorio. */
export default function ExpedienteList({
  municipioList,
  recursoAfectadoList,
  setToast,
  setExpedienteSeleccionado,
  expedienteList = [],
  onExpedienteCreado,
  isEditable = true,
}: Props) {
  const { user } = useAuth();

  return (
    <ExpedienteListBase
      adapter={expedientesSancionatorioAdapter}
      config={expedientesSancionatorioConfig}
      expedientes={expedienteList}
      onSeleccionar={setExpedienteSeleccionado}
      municipioList={municipioList}
      recursoAfectadoList={recursoAfectadoList}
      setToast={setToast}
      renderNuevoExpediente={
        isEditable
          ? ({ cerrar }) => (
              <NuevoExpediente
                userId={Number(user?.user_id)}
                municipioList={municipioList}
                recursoAfectadoList={recursoAfectadoList}
                setToast={setToast}
                onCancel={cerrar}
                addExpediente={(e) => onExpedienteCreado?.(e)}
              />
            )
          : undefined
      }
    />
  );
}
