import { useState } from "react";
import type { ActoAdministrativo, TipoNotificacion } from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";
import type { DocumentoAnexo, EtapaRecurso, SetToast } from "../types";
import EtapaContenedor from "./comun/EtapaContenedor";
import EtapaActoDocumentos from "./comun/EtapaActoDocumentos";
import ActoAuxiliar from "./comun/ActoAuxiliar";
import { useEtapaSancionatoria } from "./comun/useEtapaSancionatoria";
import { ICONOS } from "./comun/iconos";

type Props = {
  expedienteId: number;
  onStageUpdate: (stage: string) => void;
  setToast: SetToast;
  isEditable?: boolean;
  tiposNotificacion: TipoNotificacion[];
  involucrados: Involucrado[];
};

const STAGE_NAME = "RECURSO";
const TIPOS_DOCUMENTO = ["Auto Probatorio", "Informe Tecnico", "Anexos"];

export default function Recurso({
  expedienteId,
  setToast,
  onStageUpdate,
  isEditable = true,
  tiposNotificacion = [],
  involucrados = [],
}: Props) {
  const etapa = useEtapaSancionatoria<EtapaRecurso>({
    etapa: "recurso",
    expedienteId,
    nombreEtapa: STAGE_NAME,
    mensajeErrorCarga: "Error al cargar recurso.",
    setToast,
    onStageUpdate,
    alRechazarCreacion: "bloquear",
    semilla: { acto_decision: {} },
  });
  const datos = etapa.datos;
  // Se incrementa para remontar el acto de decisión al revertir un cambio inválido.
  const [versionDecision, setVersionDecision] = useState(0);

  const handleDocumentosUpdate = (documentos: DocumentoAnexo[]) => {
    etapa.setDocumentos(documentos);
    void etapa.refrescar();
  };

  const handleActoDecisionUpdate = async (acto: ActoAdministrativo) => {
    // La fecha de numerado de la decisión debe ser posterior a la del acto de etapa.
    const actoEtapa = datos?.acto_admin;
    const fechaEtapa = actoEtapa && "fecha_numerado" in actoEtapa ? actoEtapa.fecha_numerado : null;
    if (acto?.fecha_numerado && fechaEtapa) {
      if (new Date(acto.fecha_numerado) <= new Date(fechaEtapa)) {
        setToast({
          id: Date.now(),
          message: "La fecha de numerado de decisión debe ser mayor a la del acto de etapa.",
          type: "error",
        });
        await etapa.refrescar();
        setVersionDecision((v) => v + 1);
        return;
      }
    }
    etapa.actualizarDatos((d) => ({ ...d, acto_decision: acto }));
  };

  return (
    <EtapaContenedor
      expedienteId={expedienteId}
      nombreEtapa={STAGE_NAME}
      textoCarga="Obteniendo información del recurso"
      textoCrear="Para continuar, debe crear esta etapa y así poder gestionar el recurso correspondiente."
      icono={ICONOS.checkCirculo}
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
        tipoEtapa="etapa_probatoria_recurso"
        tipoBinding="etapa_san_probatoria_recurso"
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
      >
        {etapa.existeActo && (
          <ActoAuxiliar
            key={versionDecision}
            titulo="Acto Administrativo de Decisión"
            subtitulo="Gestión del acto administrativo de decisión del recurso"
            color="indigo"
            expedienteId={expedienteId}
            etapaId={etapa.etapaId ?? 0}
            tipoBinding="etapa_san_probatoria_recurso"
            acto={datos?.acto_decision}
            onActoAdminUpdate={handleActoDecisionUpdate}
            involucrados={involucrados}
            tiposNotificacion={tiposNotificacion}
            setToast={setToast}
            isEditable={isEditable}
          />
        )}
      </EtapaActoDocumentos>
    </EtapaContenedor>
  );
}
