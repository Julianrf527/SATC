import { useState } from "react";
import { apiCall, API_CONFIG } from "@shared/lib/api";
import { useTiposSancionQuery } from "../api/etapas";
import type { ActoAdministrativo, TipoNotificacion } from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";
import type { ActoEtapa, DocumentoAnexo, EtapaDecision, SetToast } from "../types";
import EtapaContenedor from "./comun/EtapaContenedor";
import EtapaActoDocumentos from "./comun/EtapaActoDocumentos";
import ActoAuxiliar from "./comun/ActoAuxiliar";
import Icono from "./comun/Icono";
import { useEtapaSancionatoria } from "./comun/useEtapaSancionatoria";
import { ICONOS } from "./comun/iconos";
import DecisionFondoData from "./decision-fondo/DecisionFondoData";
import DeleteStageModal from "./decision-fondo/DeleteStageModal";

type Props = {
  expedienteId: number;
  onStageUpdate: (stage: string) => void;
  setToast: SetToast;
  isEditable?: boolean;
  tiposNotificacion: TipoNotificacion[];
  involucrados: Involucrado[];
};

const STAGE_NAME = "DECISION DE FONDO";
const TIPOS_DOCUMENTO = ["Recurso"];
const CREABLE_ACTO_RECURSO_DEFECTO = {
  status: false,
  msg: "Debe subir un documento de tipo 'Recurso' para crear este acto.",
};

const idDeActo = (acto: ActoEtapa | null | undefined) =>
  acto && "id" in acto ? acto.id : undefined;

export default function DecisionFondo({
  expedienteId,
  setToast,
  onStageUpdate,
  isEditable = true,
  tiposNotificacion = [],
  involucrados = [],
}: Props) {
  const etapa = useEtapaSancionatoria<EtapaDecision>({
    etapa: "decision",
    expedienteId,
    nombreEtapa: STAGE_NAME,
    mensajeErrorCarga: "Error al cargar decisión de fondo.",
    setToast,
    onStageUpdate,
    alRechazarCreacion: "bloquear",
    semilla: { acto_recurso: {} },
  });
  const { data: tiposSancion = [] } = useTiposSancionQuery();
  const datos = etapa.datos;
  const [showDeleteEtapaModal, setShowDeleteEtapaModal] = useState(false);
  const [isDeletingActoEtapa, setIsDeletingActoEtapa] = useState(false);

  const actoEtapaId = idDeActo(datos?.acto_admin);
  const actoRecursoId = idDeActo(datos?.acto_recurso);
  const creableActoRecurso = datos?.creable_acto_recurso || CREABLE_ACTO_RECURSO_DEFECTO;

  // Al menos un involucrado notificado exitosamente en el acto principal.
  const actoPrincipal = datos?.acto_admin as ActoAdministrativo | undefined;
  const hayNotificacionExitosa = !!actoPrincipal?.notificacion?.involucrados?.some(
    (inv) => inv.notificacion_exitosa === true,
  );
  const canCreateActoRecurso = creableActoRecurso.status && hayNotificacionExitosa;
  const mensajeActoRecurso = !isEditable
    ? "No disponible"
    : !creableActoRecurso.status
      ? creableActoRecurso.msg
      : !hayNotificacionExitosa
        ? "Debe existir al menos una persona notificada exitosamente en el acto administrativo principal para crear este acto."
        : "";

  const refrescar = () => void etapa.refrescar();

  const handleDocumentosUpdate = (documentos: DocumentoAnexo[]) => {
    etapa.setDocumentos(documentos);
    refrescar();
  };

  const executeDeleteActoEtapa = async () => {
    setShowDeleteEtapaModal(false);
    setIsDeletingActoEtapa(true);
    const borrar = (actoId: number) =>
      apiCall(
        `${API_CONFIG.ENDPOINTS.FILE_ACTO_ADMIN_DELETE(actoId)}?expediente_id=${expedienteId}`,
        { method: "DELETE" },
      );

    try {
      // Primero el acto de recurso, si existe
      if (actoRecursoId) {
        const resRecurso = await borrar(actoRecursoId);
        if (!resRecurso.ok) {
          if (import.meta.env.DEV) console.error("Error eliminando acto de recurso:", resRecurso);
          setToast({
            id: Date.now(),
            message: "Error al eliminar el acto administrativo de recurso.",
            type: "error",
          });
          return;
        }
      }

      if (actoEtapaId) {
        const resEtapa = await borrar(actoEtapaId);
        if (resEtapa.ok) {
          setToast({
            id: Date.now(),
            message: actoRecursoId
              ? "Actos administrativos eliminados exitosamente."
              : "Acto administrativo eliminado exitosamente.",
            type: "success",
          });
          await etapa.refrescar();
        } else {
          setToast({
            id: Date.now(),
            message: resEtapa.detail || "Error al eliminar el acto administrativo.",
            type: "error",
          });
        }
      }
    } catch (e) {
      if (import.meta.env.DEV) console.error("Error eliminando actos administrativos:", e);
      setToast({ id: Date.now(), message: "Error al eliminar los actos administrativos.", type: "error" });
    } finally {
      setIsDeletingActoEtapa(false);
    }
  };

  // Con acto de recurso se pide confirmación (se borran ambos); sin él, directo.
  const handleDeleteActoEtapa = async () => {
    if (actoRecursoId) {
      setShowDeleteEtapaModal(true);
      return;
    }
    await executeDeleteActoEtapa();
  };

  return (
    <EtapaContenedor
      expedienteId={expedienteId}
      nombreEtapa={STAGE_NAME}
      textoCarga="Obteniendo información de la decisión de fondo"
      textoCrear="Para continuar, debe crear esta etapa y así poder gestionar la decisión de fondo correspondiente."
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
        tipoEtapa="etapa_decision_fondo"
        tipoBinding="etapa_san_decision_fondo"
        tipoActo="notificacion"
        acto={datos?.acto_admin}
        existeActo={etapa.existeActo}
        onActoAdminUpdate={etapa.setActo}
        customDeleteHandler={handleDeleteActoEtapa}
        involucrados={involucrados}
        tiposNotificacion={tiposNotificacion}
        documentos={etapa.documentos}
        tiposDocumento={TIPOS_DOCUMENTO}
        onDocumentosUpdate={handleDocumentosUpdate}
        setToast={setToast}
        isEditable={isEditable}
        informacion={
          <DecisionFondoData
            data={
              datos?.etapa_id && datos.tipo_sancion_id
                ? { id: datos.etapa_id, tipo_sancion_id: datos.tipo_sancion_id, detalle: datos.detalle ?? "" }
                : null
            }
            tipoSancion={tiposSancion}
            setToast={setToast}
            expedienteId={expedienteId}
            onDataUpdated={refrescar}
            isEditable={isEditable}
          />
        }
      >
        {canCreateActoRecurso && etapa.existeActo ? (
          <ActoAuxiliar
            key={actoRecursoId ?? "sin-acto-recurso"}
            titulo="Acto Administrativo de Recurso"
            subtitulo="Gestión del acto administrativo relacionado al recurso interpuesto"
            color="purple"
            expedienteId={expedienteId}
            etapaId={etapa.etapaId ?? 0}
            tipoBinding="etapa_san_decision_fondo"
            acto={datos?.acto_recurso}
            onActoAdminUpdate={(acto) =>
              etapa.actualizarDatos((d) => ({ ...d, acto_recurso: { ...acto } }))
            }
            involucrados={involucrados}
            tiposNotificacion={tiposNotificacion}
            setToast={setToast}
            isEditable={isEditable}
          />
        ) : (
          <div className="card bg-base-100 shadow-xl w-full border border-info/30">
            <div className="card-body">
              <div className="flex items-center gap-4">
                <div className="bg-info/10 rounded-full p-3">
                  <Icono d={ICONOS.info} className="h-8 w-8 text-info" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold">Acto Administrativo de Recurso no disponible</h3>
                  <p className="text-sm text-base-content/70 mt-1">{mensajeActoRecurso}</p>
                </div>
              </div>
            </div>
          </div>
        )}

        <DeleteStageModal
          isOpen={showDeleteEtapaModal}
          isDeleting={isDeletingActoEtapa}
          onClose={() => setShowDeleteEtapaModal(false)}
          onConfirm={executeDeleteActoEtapa}
        />
      </EtapaActoDocumentos>
    </EtapaContenedor>
  );
}
