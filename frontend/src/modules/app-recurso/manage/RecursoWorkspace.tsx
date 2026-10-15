import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ExpedientesWorkspace } from "@features/expedientes";
import { useCatalogosRecurso } from "../api/catalogos";
import type { NavegacionExpediente, SetToast } from "../types";
import DetalleRecurso from "./DetalleRecurso";
import { esPestana, type EtapaTabId } from "./etapasProceso";
import ExpedienteList from "./ExpedienteList";

type Props = {
  setToast: SetToast;
  /** Gestionar = true; Consulta = false (solo lectura + descarga). */
  isEditable: boolean;
};

type Seleccion = { id: number; pestana: EtapaTabId; clave: number };

/**
 * Pantalla lista + detalle de Gestionar y Consulta. Reutiliza
 * `ExpedientesWorkspace` de `@features/expedientes` tal cual; la lista y el
 * detalle son del módulo. Acepta `location.state` (`NavegacionExpediente`)
 * para abrir un expediente y una pestaña desde Mis informes.
 */
export default function RecursoWorkspace({ setToast, isEditable }: Props) {
  const location = useLocation();
  const navigate = useNavigate();
  const { catalogos, cargando } = useCatalogosRecurso(setToast);
  const [seleccion, setSeleccion] = useState<Seleccion | null>(null);

  const estado = location.state as NavegacionExpediente | null;
  useEffect(() => {
    const id = Number(estado?.expedienteIdToSelect);
    if (!Number.isInteger(id) || id <= 0) return;
    const pedida = estado?.pestanaToSelect;
    const pestana: EtapaTabId = esPestana(pedida) ? pedida : "info";
    // Clave nueva: el detalle se vuelve a montar en la pestaña pedida.
    setSeleccion({ id, pestana, clave: Date.now() });
    navigate({ pathname: location.pathname, search: location.search }, { replace: true, state: null });
  }, [estado, navigate, location.pathname, location.search]);

  const seleccionar = (id: number) =>
    setSeleccion((prev) => (prev?.id === id ? prev : { id, pestana: "info", clave: prev?.clave ?? 0 }));

  return (
    <ExpedientesWorkspace
      cargando={cargando}
      lista={
        <ExpedienteList
          catalogos={catalogos}
          setToast={setToast}
          seleccionadoId={seleccion?.id ?? null}
          onSeleccionar={seleccionar}
          puedeCrear={isEditable}
        />
      }
      detalle={
        <DetalleRecurso
          key={seleccion?.clave ?? 0}
          expedienteId={seleccion?.id ?? null}
          catalogos={catalogos}
          setToast={setToast}
          isEditable={isEditable}
          pestanaInicial={seleccion?.pestana}
        />
      }
    />
  );
}
