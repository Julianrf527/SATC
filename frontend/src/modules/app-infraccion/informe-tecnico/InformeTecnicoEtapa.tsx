import type { ReactNode } from "react";
import { useDelayedFlag } from "@shared/hooks/useDelayedFlag";
import { detalleError, esErrorDeConexion } from "../api/errors";
import { useCrearInformeEtapaMutation, useInformeEtapaQuery } from "../api/informes";
import CargueManualInforme from "../etapas/CargueManualInforme";
import {
  EtapaCargando,
  EtapaHueco,
  EtapaNoCreable,
  EtapaNoExiste,
  EtapaPorCrear,
  EtapaSinExpediente,
  IconoMas,
} from "../etapas/EtapaEstados";
import { ICONOS_ETAPA } from "../etapas/iconosEtapa";
import { useAvisoErrorCarga } from "../etapas/useAvisoErrorCarga";
import type { InformeTecnico, TipoInforme } from "../types";
import InformeTecnicoDatos from "./InformeTecnicoDatos";

type SetToast = (toast: { id: number; message: string; type: "success" | "error" }) => void;

type Props = {
  expedienteId: number;
  tipo: TipoInforme;
  /** Nombre de la etapa (toasts y estados vacíos). */
  etapa: string;
  titulo: string;
  setToast: SetToast;
  onStageUpdate: (stage: string) => void;
  isEditable?: boolean;
  /** Contenido propio de la etapa debajo de la tarjeta (p. ej. la matriz de la visita). */
  extra?: (informe: InformeTecnico) => ReactNode;
};

/**
 * Etapa de informe técnico de un expediente (Visita / Seguimiento): consulta
 * GET /etapas/informe-tecnico/{exp}/{tipo}, crea la etapa, muestra el estado
 * del proceso de revisión y abre su detalle.
 */
export default function InformeTecnicoEtapa({
  expedienteId,
  tipo,
  etapa,
  titulo,
  setToast,
  onStageUpdate,
  isEditable = false,
  extra,
}: Props) {
  const query = useInformeEtapaQuery(expedienteId, tipo);
  const crear = useCrearInformeEtapaMutation(expedienteId, tipo);
  const showLoading = useDelayedFlag(query.isPending && !!expedienteId, 300);

  useAvisoErrorCarga(query.error, setToast, {
    http: `Error al cargar la etapa ${etapa}`,
    conexion: `Error de conexión al cargar la etapa ${etapa}`,
  });

  const informe = query.data?.data ?? null;

  const crearEtapa = () =>
    crear.mutate(undefined, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Etapa creada exitosamente", type: "success" });
        onStageUpdate(etapa);
      },
      onError: (err) =>
        setToast({
          id: Date.now(),
          message: esErrorDeConexion(err) ? "Error de conexión" : (detalleError(err) ?? "Error al crear la etapa"),
          type: "error",
        }),
    });

  if (showLoading) return <EtapaCargando etapa={etapa} />;
  if (!expedienteId) return <EtapaSinExpediente isEditable={isEditable} />;
  if (query.isPending) return <EtapaHueco />;

  if (!informe && !isEditable) return <EtapaNoExiste etapa={etapa} />;
  if (!informe && !query.data?.creable) return <EtapaNoCreable motivo={query.data?.creableMsg ?? null} />;
  if (!informe) {
    return (
      <EtapaPorCrear
        etapa={etapa}
        icono={ICONOS_ETAPA.escudo}
        descripcion={`Para continuar, debe crear esta etapa y así poder gestionar la etapa ${etapa} correspondiente.`}
      >
        <button
          className="btn btn-success text-white btn-lg gap-2 shadow-md hover:shadow-lg transition-all"
          onClick={crearEtapa}
          disabled={crear.isPending}
        >
          {crear.isPending ? <span className="loading loading-spinner loading-sm" /> : <IconoMas />}
          Crear Etapa
        </button>
      </EtapaPorCrear>
    );
  }

  return (
    <>
      <InformeTecnicoDatos
        titulo={titulo}
        informe={informe}
        nota={
          isEditable ? (
            <span>
              La asignación de profesionales y el seguimiento del proceso se gestiona desde{" "}
              <strong>Informes Técnicos</strong>.
            </span>
          ) : undefined
        }
      >
        {(!informe.aceptado || informe.modo === "MANUAL") && (
          <div className="mt-4">
            <CargueManualInforme informe={informe} setToast={setToast} isEditable={isEditable} />
          </div>
        )}
      </InformeTecnicoDatos>

      {extra?.(informe)}

    </>
  );
}
