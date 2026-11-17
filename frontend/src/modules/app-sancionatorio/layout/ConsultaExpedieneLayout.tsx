import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useErrorToast } from "@shared/hooks/useErrorToast";
import type { Expediente } from "@shared/types/sancionatorio";
import {
  ExpedienteNoDisponibleModal,
  ExpedientesWorkspace,
  useExpedienteDesdeNavegacion,
  type SetToast,
} from "@features/expedientes";
import ExpedienteList from "../manage/ExpedienteList";
import DetalleExpediente from "../manage/DetalleExpediente";
import { useCatalogosSancionatorio } from "../api/catalogos";
import { useTodosExpedientesQuery } from "../api/listaExpedientes";

type Props = { setToast: SetToast };

const SIN_EXPEDIENTES: Expediente[] = [];

export default function ConsultaExpedienteLayout({ setToast }: Props) {
  const navigate = useNavigate();
  const [expedienteSeleccionado, setExpedienteSeleccionado] = useState<Expediente | null>(null);

  const catalogos = useCatalogosSancionatorio(setToast);
  // Todos los expedientes, archivados y no archivados.
  const lista = useTodosExpedientesQuery();
  useErrorToast(lista.error, setToast, "Error al cargar los expedientes");

  const { noDisponible, cerrarAviso } = useExpedienteDesdeNavegacion(
    lista.isFetching ? undefined : lista.data,
    setExpedienteSeleccionado,
  );

  const handleCerrarAviso = () => {
    cerrarAviso();
    navigate("/file/consult", { replace: true });
  };

  return (
    <>
      <ExpedientesWorkspace
        cargando={catalogos.cargando}
        lista={
          <ExpedienteList
            isEditable={false}
            setToast={setToast}
            setExpedienteSeleccionado={setExpedienteSeleccionado}
            municipioList={catalogos.municipios}
            recursoAfectadoList={catalogos.recursos}
            expedienteList={lista.data ?? SIN_EXPEDIENTES}
          />
        }
        detalle={
          <DetalleExpediente
            expedienteSeleccionado={expedienteSeleccionado}
            municipioList={catalogos.municipios}
            recursoAfectadoList={catalogos.recursos}
            setToast={setToast}
            isEditable={false}
          />
        }
      />

      <ExpedienteNoDisponibleModal
        isOpen={noDisponible}
        onClose={handleCerrarAviso}
        titulo="Expediente No Encontrado"
        subtitulo="El expediente solicitado no existe"
      >
        <p className="text-sm text-base-content/80 leading-relaxed">
          El expediente que intentas visualizar no se encuentra en el sistema o ha sido eliminado.
        </p>
      </ExpedienteNoDisponibleModal>
    </>
  );
}
