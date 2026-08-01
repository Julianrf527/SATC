import ConfirmationModal from "./ConfirmationModal";
import type { Permiso } from "../../../types/userApp";
import PermissionSelector from "./RoleForm/PermissionSelector";
import RoleConfigPanel from "./RoleForm/RoleConfigPanel";
import { useRoleForm, type SetToast } from "./RoleForm/useRoleForm";

type Props = {
  permisoList: Permiso[];
  setToast: SetToast;
};

export default function RoleForm({ permisoList = [], setToast }: Props) {
  const {
    mode,
    setMode,
    rolList,
    selectedRoleId,
    roleName,
    setRoleName,
    selectedPermissions,
    searchTerm,
    setSearchTerm,
    isSubmitting,
    confirmationModal,
    categories,
    expandedCategories,
    handleRoleSelect,
    toggleCategory,
    togglePermission,
    toggleCategoryPermissions,
    getFilteredPermissions,
    hideConfirmationModal,
    handleSubmit,
    handleDelete,
    handleClear,
  } = useRoleForm(permisoList, setToast);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      {/* Panel de configuración */}
      <RoleConfigPanel
        mode={mode}
        onModeChange={setMode}
        rolList={rolList}
        selectedRoleId={selectedRoleId}
        onRoleSelect={handleRoleSelect}
        roleName={roleName}
        onRoleNameChange={setRoleName}
        selectedCount={selectedPermissions.length}
        totalPermissions={permisoList.length}
        isSubmitting={isSubmitting}
        onSubmit={handleSubmit}
        onDelete={handleDelete}
        onClear={handleClear}
      />

      {/* Panel de permisos */}
      <PermissionSelector
        categories={categories}
        searchTerm={searchTerm}
        onSearchTermChange={setSearchTerm}
        expandedCategories={expandedCategories}
        selectedPermissions={selectedPermissions}
        getFilteredPermissions={getFilteredPermissions}
        onToggleCategory={toggleCategory}
        onToggleCategoryPermissions={toggleCategoryPermissions}
        onTogglePermission={togglePermission}
      />

      {/* Modal de confirmación dinámico */}
      <ConfirmationModal
        isOpen={confirmationModal.isOpen}
        onClose={hideConfirmationModal}
        onConfirm={confirmationModal.onConfirm}
        typeOperation={confirmationModal.typeOperation}
        typeChange={confirmationModal.typeChange}
        itemIdentifier={confirmationModal.itemIdentifier}
        isSubmitting={isSubmitting}
      />
    </div>
  );
}
