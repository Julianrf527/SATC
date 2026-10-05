import ConfirmationModal from "./ConfirmationModal";
import type { Permiso, SetToast } from "../types";
import PermissionEditorPanel from "./permission-form/PermissionEditorPanel";
import PermissionListPanel from "./permission-form/PermissionListPanel";
import { usePermissionForm } from "./permission-form/usePermissionForm";

type Props = {
  permisoList: Permiso[];
  setToast: SetToast;
};

export default function PermissionForm({ permisoList = [], setToast }: Props) {
  const form = usePermissionForm(permisoList, setToast);

  return (
    <>
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row divide-y lg:divide-y-0 lg:divide-x divide-base-300">
        {/* Panel de formulario */}
        <PermissionEditorPanel
          mode={form.mode}
          onModeChange={form.changeMode}
          permisoList={permisoList}
          selectedPermissionId={form.selectedPermissionId}
          onPermissionSelect={form.handlePermissionSelect}
          permissionName={form.permissionName}
          onPermissionNameChange={form.setPermissionName}
          menuPath={form.menuPath}
          onMenuPathChange={form.setMenuPath}
          isSubmitting={form.isSubmitting}
          onSubmit={form.handleSubmit}
          onDelete={form.handleDelete}
          onClear={form.handleClear}
        />

        {/* Panel de lista de permisos */}
        <PermissionListPanel
          groups={form.groups}
          filteredCount={form.filteredCount}
          searchTerm={form.searchTerm}
          onSearchTermChange={form.setSearchTerm}
          onEdit={form.editPermission}
        />
      </div>

      {/* Modal de confirmación dinámico */}
      <ConfirmationModal
        isOpen={form.confirmacion.isOpen}
        typeOperation={form.confirmacion.typeOperation}
        typeChange={form.confirmacion.typeChange}
        itemIdentifier={form.confirmacion.itemIdentifier}
        isSubmitting={form.isSubmitting}
        onConfirm={form.confirmacion.onConfirm}
        onClose={form.cerrarConfirmacion}
      />
    </>
  );
}
