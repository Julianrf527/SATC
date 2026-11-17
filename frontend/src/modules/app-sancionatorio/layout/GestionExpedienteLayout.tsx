import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@shared/context/AuthContext";
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
import {
  useExpedientesEncargadoQuery,
  useInvalidarListaExpedientes,
} from "../api/listaExpedientes";

type Props = { setToast: SetToast };

const SIN_EXPEDIENTES: Expediente[] = [];

export default function GestionExpedienteLayout({ setToast }: Props) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [expedienteSeleccionado, setExpedienteSeleccionado] = useState<Expediente | null>(null);

  const catalogos = useCatalogosSancionatorio(setToast);
  const lista = useExpedientesEncargadoQuery(user?.user_id);
  useErrorToast(lista.error, setToast, "Error al cargar los expedientes");
  const invalidarLista = useInvalidarListaExpedientes();

  const { noDisponible, cerrarAviso } = useExpedienteDesdeNavegacion(
    lista.isFetching ? undefined : lista.data,
    setExpedienteSeleccionado,
  );

  // El toast de éxito lo da InformacionExpedienteData (tras el PUT); aquí no se repite.
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
    navigate("/file/manage", { replace: true });
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
            expedienteList={lista.data ?? SIN_EXPEDIENTES}
            onExpedienteCreado={() => void invalidarLista()}
          />
        }
        detalle={
          <DetalleExpediente
            expedienteSeleccionado={expedienteSeleccionado}
            municipioList={catalogos.municipios}
            recursoAfectadoList={catalogos.recursos}
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
