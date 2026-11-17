import { useAuth } from "@shared/context/AuthContext";
import type { Municipio, ModeloGenerico } from "@shared/types/common";
import { ExpedienteList as ExpedienteListBase, type SetToast } from "@features/expedientes";
import NuevoExpediente from "./NuevoExpediente";
import FiltroTiposAfectacion from "./FiltroTiposAfectacion";
import {
  expedientesInfraccionAdapter,
  expedientesInfraccionConfig,
  type AlcanceExpedientes,
} from "./expedientesAdapter";
import type { Expediente, Quejoso, TipoAfectacion } from "../types";

type Props = {
  municipioList: Municipio[];
  recursoAfectadoList: ModeloGenerico[];
  tipoAfectacionList: TipoAfectacion[];
  quejosoList: Quejoso[];
  setQuejosoList: (quejosos: Quejoso[]) => void;
  setToast: SetToast;
  setExpedienteSeleccionado: (expediente: Expediente | null) => void;
  expedienteList: Expediente[];
  /** Tras crear un expediente (p. ej. invalidar el listado). */
  onExpedienteCreado?: (expediente: Expediente) => void;
  isEditable?: boolean;
  /** Alcance de la búsqueda avanzada; la vista de consulta pasa "todos". */
  alcance?: AlcanceExpedientes;
};

/** Monta la lista compartida de `@features/expedientes` con el adapter de infracción. */
export default function ExpedienteList({
  municipioList,
  recursoAfectadoList,
  tipoAfectacionList,
  quejosoList,
  setQuejosoList,
  setToast,
  setExpedienteSeleccionado,
  expedienteList = [],
  onExpedienteCreado,
  isEditable = true,
  alcance = "propios",
}: Props) {
  const { user } = useAuth();

  return (
    <ExpedienteListBase
      adapter={expedientesInfraccionAdapter(alcance)}
      config={expedientesInfraccionConfig}
      expedientes={expedienteList}
      onSeleccionar={setExpedienteSeleccionado}
      municipioList={municipioList}
      recursoAfectadoList={recursoAfectadoList}
      setToast={setToast}
      renderFiltrosAvanzadosExtra={(ctx) => (
        <FiltroTiposAfectacion
          {...ctx}
          recursoAfectadoList={recursoAfectadoList}
          tipoAfectacionList={tipoAfectacionList}
        />
      )}
      renderNuevoExpediente={
        isEditable
          ? ({ cerrar }) => (
              <NuevoExpediente
                userId={Number(user?.user_id)}
                municipioList={municipioList}
                recursoAfectadoList={recursoAfectadoList}
                tipoAfectacionList={tipoAfectacionList}
                quejosoList={quejosoList}
                setQuejosoList={setQuejosoList}
                setToast={setToast}
                onCancel={cerrar}
                agregarExpediente={(e) => onExpedienteCreado?.(e)}
              />
            )
          : undefined
      }
    />
  );
}
