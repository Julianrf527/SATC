import type { TipoNotificacion } from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";
import { useTiposCesacionQuery } from "../api/etapas";
import type { EtapaCesacion, SetToast } from "../types";
import EtapaContenedor from "./comun/EtapaContenedor";
import EtapaActoDocumentos from "./comun/EtapaActoDocumentos";
import { useEtapaSancionatoria } from "./comun/useEtapaSancionatoria";
import CesacionData from "./cesacion/CesacionData";

type Props = {
  expedienteId: number;
  onStageUpdate: (stage: string) => void;
  setToast: SetToast;
  isEditable?: boolean;
  tiposNotificacion: TipoNotificacion[];
  involucrados: Involucrado[];
};

const STAGE_NAME = "CESACION";
const TIPOS_DOCUMENTO = ["Recurso"];

export default function Cesacion({
  expedienteId,
  setToast,
  onStageUpdate,
  isEditable = true,
  tiposNotificacion = [],
  involucrados = [],
}: Props) {
  const { data: tiposCesacion = [] } = useTiposCesacionQuery();
  const etapa = useEtapaSancionatoria<EtapaCesacion>({
    etapa: "cesacion",
    expedienteId,
    nombreEtapa: STAGE_NAME,
    mensajeErrorCarga: "Error al cargar cesación.",
    setToast,
    onStageUpdate,
    alRechazarCreacion: "bloquear",
  });
  const datos = etapa.datos;

  return (
    <EtapaContenedor
      expedienteId={expedienteId}
      nombreEtapa={STAGE_NAME}
      textoCarga="Obteniendo información de la cesación"
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
        tipoEtapa="etapa_cesacion"
        tipoBinding="etapa_san_cesacion"
        tipoActo="notificacion"
        acto={datos?.acto_admin}
        existeActo={etapa.existeActo}
        onActoAdminUpdate={etapa.setActo}
        involucrados={involucrados}
        tiposNotificacion={tiposNotificacion}
        documentos={etapa.documentos}
        tiposDocumento={TIPOS_DOCUMENTO}
        onDocumentosUpdate={etapa.setDocumentos}
        setToast={setToast}
        isEditable={isEditable}
        avisoSinActo={{
          titulo: "Información y documentos no disponibles",
          texto: "Debe crear un acto administrativo antes de registrar información o subir documentos.",
        }}
        informacion={
          <CesacionData
            data={
              datos?.etapa_id
                ? { id: datos.etapa_id, tipo_cesacion_id: datos.tipo_cesacion_id ?? undefined }
                : null
            }
            tipoMedida={tiposCesacion}
            setToast={setToast}
            etapaId={etapa.etapaId ?? 0}
            expedienteId={expedienteId}
            isEditable={isEditable}
          />
        }
      />
    </EtapaContenedor>
  );
}
