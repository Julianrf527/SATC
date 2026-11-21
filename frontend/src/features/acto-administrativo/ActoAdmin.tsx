import { openDocumentById } from "@shared/lib/documentViewer";
import type {
  ActoAdministrativo,
  TipoNotificacion,
} from "@shared/types/sancionatorio";
import type { Involucrado } from "@shared/types/involucrado";
import ActoAdminCard from "./ActoAdminCard";
import ActoAdminModal from "./ActoAdminModal";
import ActoAdminEmptyState from "./ActoAdminEmptyState";
import ConfirmDeleteModal from "./ConfirmDeleteModal";
import ComunicacionModal from "./ComunicacionModal";
import NotificacionModal from "./NotificationModal";
import {
  DEFAULT_ENDPOINTS,
  type ActoAdminEndpoints,
  type ActoAdminFormData,
  type ActoAdminOrEmpty,
  type ActoAdminSaveResult,
  type ActoAdminStageBinding,
  type SetToast,
  type TipoActo,
} from "./actoAdminConfig";
import { useActoAdminActions } from "./useActoAdminActions";
import { useNotificacionActions } from "./useNotificacionActions";

type Props = {
  expedienteId: number;
  actoAdmin: ActoAdminOrEmpty;
  etapaId: number;
  tipoActo: TipoActo;
  setToast: SetToast;
  isEditable?: boolean;
  setExistActoAdmin?: (exist: boolean) => void;
  onActoAdminUpdate?: (actoAdmin: ActoAdministrativo) => void;
  involucrados?: Involucrado[];
  tiposNotificacion?: TipoNotificacion[];
  customDeleteHandler?: () => Promise<void>;
  nivelAuxiliar?: boolean | null;
  endpoints?: ActoAdminEndpoints;
  stageBinding?: ActoAdminStageBinding;
  embedded?: boolean;
  /** Crear el acto desde el estado vacío (default true). */
  allowCreate?: boolean;
  /** Eliminar el acto (default true). */
  allowDelete?: boolean;
  /** Reemplazar el PDF al editar (default true). */
  allowDocumentChange?: boolean;
  /**
   * Contenido propio cuando la etapa aún no tiene acto (reemplaza el estado
   * vacío). Recibe `abrirCrear` para abrir el modal de creación (solo
   * funciona si `allowCreate` y `isEditable`).
   */
  renderEmpty?: (abrirCrear: () => void) => React.ReactNode;
  /**
   * Modal propio para crear el acto (en lugar de `ActoAdminModal`). Recibe el
   * guardado de la feature: actualiza el estado local y `onActoAdminUpdate`.
   */
  renderModalCrear?: (props: {
    onSave: (data: ActoAdminFormData) => Promise<ActoAdminSaveResult>;
    onClose: () => void;
  }) => React.ReactNode;
};

export default function ActoAdmin({
  expedienteId,
  actoAdmin,
  etapaId,
  tipoActo,
  setToast,
  isEditable = true,
  setExistActoAdmin,
  onActoAdminUpdate,
  involucrados = [],
  tiposNotificacion = [],
  customDeleteHandler,
  nivelAuxiliar = null,
  endpoints,
  stageBinding,
  embedded = false,
  allowCreate = true,
  allowDelete = true,
  allowDocumentChange = true,
  renderEmpty,
  renderModalCrear,
}: Props) {
  const apiEndpoints = endpoints ?? DEFAULT_ENDPOINTS;

  const acto = useActoAdminActions({
    expedienteId,
    actoAdmin,
    etapaId,
    apiEndpoints,
    stageBinding,
    nivelAuxiliar,
    customDeleteHandler,
    setToast,
    setExistActoAdmin,
    onActoAdminUpdate,
  });

  const { localActoAdmin, hasActoAdmin } = acto;

  const isNotificacion = tipoActo === "notificacion";
  const isComunicacion =
    tipoActo === "comunicacion" && !!apiEndpoints.comunicacion;

  const notif = useNotificacionActions({
    expedienteId,
    apiEndpoints,
    localActoAdmin,
    setLocalActoAdmin: acto.setLocalActoAdmin,
    hasActoAdmin,
    isNotificacion,
    setToast,
    onActoAdminUpdate,
  });

  const handleViewDocument = (fileId: number) => {
    openDocumentById(fileId);
  };

  if (!hasActoAdmin) {
    const cerrarCrear = () => acto.setShowActoModal(false);
    const modalCrear = isEditable && allowCreate && (renderModalCrear ? (
      acto.showActoModal && renderModalCrear({ onSave: acto.handleSaveActoAdmin, onClose: cerrarCrear })
    ) : (
      <ActoAdminModal
        isOpen={acto.showActoModal}
        onClose={() => acto.setShowActoModal(false)}
        onSave={acto.handleSaveActoAdmin}
        editActoAdmin={null}
      />
    ));
    if (renderEmpty) {
      return (
        <>
          {renderEmpty(() => acto.setShowActoModal(true))}
          {modalCrear}
        </>
      );
    }
    return (
      <ActoAdminEmptyState
        isEditable={isEditable && allowCreate}
        onCreate={() => acto.setShowActoModal(true)}
      >
        {modalCrear}
      </ActoAdminEmptyState>
    );
  }

  return (
    <div className={embedded ? "space-y-4" : "mx-auto space-y-6"}>
      <ActoAdminCard
        actoAdmin={localActoAdmin as ActoAdministrativo}
        expedienteId={expedienteId}
        tipoActo={tipoActo}
        onEdit={() => acto.setShowActoModal(true)}
        onDelete={() => acto.setShowDeleteModal(true)}
        onAddComunicacion={
          isComunicacion ? acto.handleAddComunicacion : undefined
        }
        onEditComunicacion={
          isComunicacion ? acto.handleEditComunicacion : undefined
        }
        onComunicacionDeleted={
          isComunicacion ? acto.handleComunicacionDeleted : undefined
        }
        onAddNotificacion={
          isNotificacion ? notif.handleAddNotificacion : undefined
        }
        onEditNotificacion={
          isNotificacion ? notif.handleEditNotificacion : undefined
        }
        onDeleteNotificacion={
          isNotificacion ? notif.handleDeleteNotificacion : undefined
        }
        onViewDocument={handleViewDocument}
        involucrados={involucrados}
        tiposNotificacion={tiposNotificacion}
        setToast={setToast}
        isEditable={isEditable}
        comunicacionDeleteEndpoint={apiEndpoints.comunicacion?.delete}
        embedded={embedded}
        allowDelete={allowDelete}
      />

      {isEditable && (
        <>
          <ActoAdminModal
            isOpen={acto.showActoModal}
            onClose={() => acto.setShowActoModal(false)}
            onSave={acto.handleSaveActoAdmin}
            editActoAdmin={
              hasActoAdmin ? (localActoAdmin as ActoAdministrativo) : null
            }
            allowDocumentChange={allowDocumentChange}
          />

          {isComunicacion && apiEndpoints.comunicacion && (
            <ComunicacionModal
              isOpen={acto.showComunicacionModal}
              onClose={() => {
                acto.setShowComunicacionModal(false);
                acto.setEditingComunicacion(false);
              }}
              expedienteId={expedienteId}
              actoAdminId={(localActoAdmin as ActoAdministrativo).id}
              editComunicacion={
                acto.editingComunicacion && hasActoAdmin
                  ? (localActoAdmin as ActoAdministrativo).comunicacion || null
                  : null
              }
              endpoints={apiEndpoints.comunicacion}
              onSuccess={acto.handleComunicacionSuccess}
            />
          )}

          {isNotificacion && (
            <NotificacionModal
              isOpen={notif.showNotificacionModal}
              onClose={() => {
                notif.setShowNotificacionModal(false);
                notif.setEditingNotificacion(null);
              }}
              editingNotificacion={notif.editingNotificacion}
              involucrados={involucrados}
              yaNotificados={notif.getYaNotificados()}
              tiposNotificacion={tiposNotificacion}
              onSave={notif.handleSaveNotificacion}
              isEditable={isEditable}
              notificacionesExistentes={notif.getNotificacionesExistentes()}
            />
          )}

          <ConfirmDeleteModal
            isOpen={acto.showDeleteModal}
            onClose={() => acto.setShowDeleteModal(false)}
            onConfirm={acto.handleDeleteActoAdmin}
            type="acto"
            itemIdentifier={(
              localActoAdmin as ActoAdministrativo
            ).numerado?.toString()}
            tipoActo={tipoActo}
          />
        </>
      )}
    </div>
  );
}
