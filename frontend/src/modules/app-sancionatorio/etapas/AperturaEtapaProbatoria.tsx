import type { TipoNotificacion } from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";
import type { EtapaBase, SetToast } from "../types";
import EtapaContenedor from "./comun/EtapaContenedor";
import EtapaActoDocumentos from "./comun/EtapaActoDocumentos";
import { useEtapaSancionatoria } from "./comun/useEtapaSancionatoria";

type Props = {
  expedienteId: number;
  onStageUpdate: (stage: string) => void;
  setToast: SetToast;
  isEditable?: boolean;
  tiposNotificacion: TipoNotificacion[];
  involucrados: Involucrado[];
};

const STAGE_NAME = "APERTURA ETAPA PROBATORIA";
const TIPOS_DOCUMENTO = [
  "Informe Tecnico",
  "Informe Autoridad Oficial",
  "Recurso",
];

export default function AperturaEtapaProbatoria({
  expedienteId,
  setToast,
  onStageUpdate,
  isEditable = true,
  tiposNotificacion = [],
  involucrados = [],
}: Props) {
  const etapa = useEtapaSancionatoria<EtapaBase>({
    etapa: "apertura",
    expedienteId,
    nombreEtapa: STAGE_NAME,
    mensajeErrorCarga: "Error al cargar apertura etapa probatoria.",
    setToast,
    onStageUpdate,
    alRechazarCreacion: "bloquear",
  });

  return (
    <EtapaContenedor
      expedienteId={expedienteId}
      nombreEtapa={STAGE_NAME}
      textoCarga="Obteniendo información de la apertura etapa probatoria"
      textoCrear="Para continuar, debe crear esta etapa y así poder gestionar las notificaciones correspondientes."
      isEditable={isEditable}
      cargando={etapa.cargando}
      mostrarCarga={etapa.mostrarCarga}
      etapaExiste={etapa.etapaExiste}
      creable={etapa.creable}
      creando={etapa.creando}
      onCrear={etapa.crearEtapa}
    >
      <EtapaActoDocumentos
        expedienteId={expedienteId}
        etapaId={etapa.etapaId ?? 0}
        tipoEtapa="etapa_apertura_probatoria"
        tipoBinding="etapa_san_apertura_probatoria"
        tipoActo="notificacion"
        acto={etapa.datos?.acto_admin}
        existeActo={etapa.existeActo}
        onActoAdminUpdate={etapa.setActo}
        involucrados={involucrados}
        tiposNotificacion={tiposNotificacion}
        documentos={etapa.documentos}
        tiposDocumento={TIPOS_DOCUMENTO}
        onDocumentosUpdate={etapa.setDocumentos}
        setToast={setToast}
        isEditable={isEditable}
      />
    </EtapaContenedor>
  );
}
