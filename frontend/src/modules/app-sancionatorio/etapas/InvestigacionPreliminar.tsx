import type { EtapaBase, SetToast } from "../types";
import EtapaContenedor from "./comun/EtapaContenedor";
import EtapaActoDocumentos from "./comun/EtapaActoDocumentos";
import { useEtapaSancionatoria } from "./comun/useEtapaSancionatoria";

type Props = {
  expedienteId: number;
  onStageUpdate: (stage: string) => void;
  setToast: SetToast;
  isEditable?: boolean;
};

const STAGE_NAME = "INDAGACION PRELIMINAR";
const TIPOS_DOCUMENTO = [
  "Concepto Tecnico",
  "Respuesta Entidad Oficial",
  "Respuesta Infractor",
];

export default function InvestigacionPreliminar({
  expedienteId,
  onStageUpdate,
  setToast,
  isEditable = true,
}: Props) {
  const etapa = useEtapaSancionatoria<EtapaBase>({
    etapa: "indagacion",
    expedienteId,
    nombreEtapa: STAGE_NAME,
    mensajeErrorCarga: "Error al cargar la indagación preliminar.",
    setToast,
    onStageUpdate,
    alRechazarCreacion: "avisar",
  });

  return (
    <EtapaContenedor
      expedienteId={expedienteId}
      nombreEtapa={STAGE_NAME}
      textoCarga="Obteniendo información de la indagación preliminar"
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
        tipoEtapa="etapa_indagacion"
        tipoBinding="etapa_san_indagacion"
        tipoActo="comunicacion"
        acto={etapa.datos?.acto_admin}
        existeActo={etapa.existeActo}
        onActoAdminUpdate={etapa.setActo}
        documentos={etapa.documentos}
        tiposDocumento={TIPOS_DOCUMENTO}
        onDocumentosUpdate={etapa.setDocumentos}
        setToast={setToast}
        isEditable={isEditable}
      />
    </EtapaContenedor>
  );
}
