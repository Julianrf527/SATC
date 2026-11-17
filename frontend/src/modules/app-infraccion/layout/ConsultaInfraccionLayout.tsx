import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@shared/context/AuthContext";
import { useErrorToast } from "@shared/hooks/useErrorToast";
import {
  ExpedienteNoDisponibleModal,
  ExpedientesWorkspace,
  useExpedienteDesdeNavegacion,
  type SetToast,
} from "@features/expedientes";
import ExpedienteList from "../manage/ExpedienteList";
import DetalleInfraccion from "../manage/DetalleInfraccion";
import { useCatalogosInfraccion } from "../api/catalogos";
import {
  useTodosExpedientesQuery,
  useInvalidarListaExpedientes,
} from "../api/listaExpedientes";
import type { Expediente } from "../types";

type Props = { setToast: SetToast };

const SIN_EXPEDIENTES: Expediente[] = [];

export default function ConsultaInfraccionLayout({ setToast }: Props) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [expedienteSeleccionado, setExpedienteSeleccionado] = useState<Expediente | null>(null);

  const catalogos = useCatalogosInfraccion(setToast);
  const lista = useTodosExpedientesQuery(!!user);
  useErrorToast(lista.error, setToast, "Error al cargar los expedientes");
  const invalidarLista = useInvalidarListaExpedientes();

  const { noDisponible, cerrarAviso } = useExpedienteDesdeNavegacion(
    lista.isFetching ? undefined : lista.data,
    setExpedienteSeleccionado,
  );

  // Las ediciones del expediente (datos, etapas, involucrados...) invalidan
  // el detalle y este listado desde sus mutaciones (api/invalidar.ts).

  const handleArchiveSuccess = () => {
    setExpedienteSeleccionado(null);
    void invalidarLista();
  };

  const handleCerrarAviso = () => {
    cerrarAviso();
    navigate("/infraction/consult", { replace: true });
  };

  return (
    <>
      <ExpedientesWorkspace
        cargando={catalogos.cargando}
        lista={
          <ExpedienteList
            isEditable={false}
            alcance="todos"
            setToast={setToast}
            setExpedienteSeleccionado={setExpedienteSeleccionado}
            municipioList={catalogos.municipios}
            recursoAfectadoList={catalogos.recursos}
            tipoAfectacionList={catalogos.tiposAfectacion}
            expedienteList={lista.data ?? SIN_EXPEDIENTES}
            quejosoList={catalogos.quejosos}
            setQuejosoList={catalogos.setQuejosos}
          />
        }
        detalle={
          <DetalleInfraccion
            expedienteSeleccionado={expedienteSeleccionado}
            municipioList={catalogos.municipios}
            recursoAfectadoList={catalogos.recursos}
            tipoAfectacionList={catalogos.tiposAfectacion}
            quejosoList={catalogos.quejosos}
            setToast={setToast}
            isEditable={false}
            onArchiveSuccess={handleArchiveSuccess}
          />
        }
      />

      <ExpedienteNoDisponibleModal isOpen={noDisponible} onClose={handleCerrarAviso} />
    </>
  );
}
