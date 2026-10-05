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
  useExpedientesEncargadoQuery,
  useInvalidarListaExpedientes,
} from "../api/listaExpedientes";
import type { Expediente } from "../types";

type Props = { setToast: SetToast };

const SIN_EXPEDIENTES: Expediente[] = [];

export default function GestionInfraccionLayout({ setToast }: Props) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [expedienteSeleccionado, setExpedienteSeleccionado] = useState<Expediente | null>(null);

  const catalogos = useCatalogosInfraccion(setToast);
  const lista = useExpedientesEncargadoQuery(user?.user_id);
  useErrorToast(lista.error, setToast, "Error al cargar los expedientes");
  const invalidarLista = useInvalidarListaExpedientes();

  const { noDisponible, cerrarAviso } = useExpedienteDesdeNavegacion(
    lista.isFetching ? undefined : lista.data,
    setExpedienteSeleccionado,
  );

  // El toast de éxito lo da el formulario de información (onSuccess del mutate).
  const handleExpedienteUpdate = (actualizado: Expediente) => {
    setExpedienteSeleccionado({ ...actualizado });
    void invalidarLista();
  };

  const handleArchiveSuccess = () => {
    setExpedienteSeleccionado(null);
    void invalidarLista();
  };

  const handleCerrarAviso = () => {
    cerrarAviso();
    navigate("/infraction/manage", { replace: true });
  };

  return (
    <>
      <ExpedientesWorkspace
        cargando={catalogos.cargando}
        lista={
          <ExpedienteList
            setToast={setToast}
            setExpedienteSeleccionado={setExpedienteSeleccionado}
            municipioList={catalogos.municipios}
            recursoAfectadoList={catalogos.recursos}
            tipoAfectacionList={catalogos.tiposAfectacion}
            expedienteList={lista.data ?? SIN_EXPEDIENTES}
            quejosoList={catalogos.quejosos}
            setQuejosoList={catalogos.setQuejosos}
            onExpedienteCreado={() => void invalidarLista()}
          />
        }
        detalle={
          <DetalleInfraccion
            expedienteSeleccionado={expedienteSeleccionado}
            municipioList={catalogos.municipios}
            recursoAfectadoList={catalogos.recursos}
            tipoAfectacionList={catalogos.tiposAfectacion}
            quejosoList={catalogos.quejosos}
            setQuejosoList={catalogos.setQuejosos}
            setToast={setToast}
            onUpdate={handleExpedienteUpdate}
            onArchiveSuccess={handleArchiveSuccess}
          />
        }
      />

      <ExpedienteNoDisponibleModal isOpen={noDisponible} onClose={handleCerrarAviso} />
    </>
  );
}
