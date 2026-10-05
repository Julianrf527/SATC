import type { TipoNotificacion } from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";
import type { DocumentoAnexo, EtapaFormulacion, SetToast } from "../types";
import EtapaContenedor from "./comun/EtapaContenedor";
import EtapaActoDocumentos from "./comun/EtapaActoDocumentos";
import { useEtapaSancionatoria } from "./comun/useEtapaSancionatoria";
import FormulacionCargosData from "./formulacion-cargos/FormulacionCargosData";

type Props = {
  expedienteId: number;
  onStageUpdate: (stage: string) => void;
  setToast: SetToast;
  isEditable?: boolean;
  tiposNotificacion: TipoNotificacion[];
  involucrados: Involucrado[];
};

const STAGE_NAME = "FORMULACION DE CARGOS";
const TIPOS_DOCUMENTO = ["Informe Tecnico", "Anexos"];

export default function FormulacionCargos({
  expedienteId,
  setToast,
  onStageUpdate,
  isEditable = true,
  tiposNotificacion = [],
  involucrados = [],
}: Props) {
  const etapa = useEtapaSancionatoria<EtapaFormulacion>({
    etapa: "formulacion",
    expedienteId,
    nombreEtapa: STAGE_NAME,
    mensajeErrorCarga: "Error al cargar formulación de cargos.",
    setToast,
    onStageUpdate,
    alRechazarCreacion: "bloquear",
  });
  const datos = etapa.datos;
  // La información vive en la propia etapa: existe en cuanto existe la etapa
  // (descargos null = "No Aplica").
  const informacion = datos?.etapa_id
    ? { id: datos.etapa_id, descargos: datos.descargos ?? null, documento_id: datos.documento_id }
    : undefined;

  const handleDocumentosUpdate = (documentos: DocumentoAnexo[]) => {
    etapa.setDocumentos(documentos);
    void etapa.refrescar();
  };

  return (
    <EtapaContenedor
      expedienteId={expedienteId}
      nombreEtapa={STAGE_NAME}
      textoCarga="Obteniendo información de la formulación de cargos"
      textoCrear="Para continuar, debe crear esta etapa y así poder gestionar la formulación de cargos correspondiente."
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
        tipoEtapa="etapa_formulacion_cargos"
        tipoBinding="etapa_san_formulacion_cargos"
        tipoActo="notificacion"
        acto={datos?.acto_admin}
        existeActo={etapa.existeActo}
        onActoAdminUpdate={etapa.setActo}
        involucrados={involucrados}
        tiposNotificacion={tiposNotificacion}
        documentos={etapa.documentos}
        tiposDocumento={TIPOS_DOCUMENTO}
        onDocumentosUpdate={handleDocumentosUpdate}
        setToast={setToast}
        isEditable={isEditable}
        avisoSinActo={{
          titulo: "Información y documentos no disponibles",
          texto: "Debe crear un acto administrativo antes de registrar información o subir documentos.",
        }}
        informacion={
          <FormulacionCargosData
            data={informacion}
            setToast={setToast}
            etapaId={etapa.etapaId ?? 0}
            expedienteId={expedienteId}
            onDataUpdated={() => void etapa.refrescar()}
            isEditable={isEditable}
          />
        }
      />
    </EtapaContenedor>
  );
}
