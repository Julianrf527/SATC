import { useState, type ReactNode } from "react";
import { useDelayedFlag } from "@shared/hooks/useDelayedFlag";
import { detalleError, esErrorDeConexion } from "../api/errors";
import { useCrearInformeEtapaMutation, useInformeEtapaQuery } from "../api/informes";
import BotonCargueDirecto from "../etapas/BotonCargueDirecto";
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
import TarjetaEtapa from "../etapas/TarjetaEtapa";
import { useEsSuperGestion } from "../etapas/useEsSuperGestion";
import { useAvisoErrorCarga } from "../etapas/useAvisoErrorCarga";
import type { CodigoEtapa } from "../manage/etapasProceso";
import type { InformeTecnico, TipoInforme } from "../types";
import InformeTecnicoDatos from "./InformeTecnicoDatos";
import SuperCargueInformeModal from "./SuperCargueInformeModal";

type SetToast = (toast: { id: number; message: string; type: "success" | "error" }) => void;

type Props = {
  expedienteId: number;
  tipo: TipoInforme;
  /** Nombre de la etapa (toasts y estados vacíos). */
  etapa: string;
  titulo: string;
  /** Etapa del proceso (recuadro "Etapa N · Nombre"). */
  codigoEtapa: CodigoEtapa;
  setToast: SetToast;
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
  codigoEtapa,
  setToast,
  isEditable = false,
  extra,
}: Props) {
  const query = useInformeEtapaQuery(expedienteId, tipo);
  const crear = useCrearInformeEtapaMutation(expedienteId, tipo);
  const showLoading = useDelayedFlag(query.isPending && !!expedienteId, 300);
  const esSuper = useEsSuperGestion();
  const [cargueDirecto, setCargueDirecto] = useState(false);

  useAvisoErrorCarga(query.error, setToast, {
    http: `Error al cargar la etapa ${etapa}`,
    conexion: `Error de conexión al cargar la etapa ${etapa}`,
  });

  const informe = query.data?.data ?? null;

  const crearEtapa = () =>
    crear.mutate(undefined, {
      onSuccess: () => {
        setToast({ id: Date.now(), message: "Etapa creada exitosamente", type: "success" });
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
    <TarjetaEtapa
      etapa={codigoEtapa}
      // Super gestión: cargue directo del informe (como cada nodo de recurso).
      acciones={isEditable && esSuper ? <BotonCargueDirecto onClick={() => setCargueDirecto(true)} /> : undefined}
    >
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
      />

      {extra?.(informe)}

      {cargueDirecto && (
        <SuperCargueInformeModal
          informe={informe}
          titulo={`Informe técnico · ${etapa}`}
          setToast={setToast}
          onClose={() => setCargueDirecto(false)}
        />
      )}
    </TarjetaEtapa>
  );
}
