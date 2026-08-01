import { useState } from 'react';

export interface UseConfirmationOptions {
  title: string;
  message: string;
  operation: 'create' | 'update' | 'delete';
  entityType?: string;
  entityName?: string;
}

export interface ConfirmationState {
  isOpen: boolean;
  isSubmitting: boolean;
  options: UseConfirmationOptions;
  onConfirm: (() => void) | null;
}

export const useConfirmation = () => {
  const [state, setState] = useState<ConfirmationState>({
    isOpen: false,
    isSubmitting: false,
    options: {
      title: '',
      message: '',
      operation: 'create'
    },
    onConfirm: null
  });

  const openConfirmation = (
    options: UseConfirmationOptions,
    onConfirm: () => void | Promise<void>
  ) => {
    setState({
      isOpen: true,
      isSubmitting: false,
      options,
      onConfirm: onConfirm
    });
  };

  const closeConfirmation = () => {
    setState(prev => ({
      ...prev,
      isOpen: false,
      isSubmitting: false
    }));
  };

  const handleConfirm = async () => {
    if (!state.onConfirm) return;

    try {
      setState(prev => ({ ...prev, isSubmitting: true }));

      // El callback puede ser síncrono o asíncrono.
      await state.onConfirm();

      closeConfirmation();
    } catch (error) {
      if (import.meta.env.DEV) console.error('Error durante la confirmación:', error);
      // El modal queda abierto a propósito para que el usuario vea el error.
      setState(prev => ({ ...prev, isSubmitting: false }));
    }
  };

  const confirmCreate = (
    entityType: string,
    entityName: string | undefined,
    onConfirm: () => void | Promise<void>
  ) => {
    openConfirmation(
      {
        title: `Crear ${entityType}`,
        message: `¿Estás seguro que deseas crear ${entityName ? `"${entityName}"` : `este ${entityType}`}?`,
        operation: 'create',
        entityType,
        entityName
      },
      onConfirm
    );
  };

  const confirmUpdate = (
    entityType: string,
    entityName: string | undefined,
    onConfirm: () => void | Promise<void>
  ) => {
    openConfirmation(
      {
        title: `Actualizar ${entityType}`,
        message: `¿Estás seguro que deseas guardar los cambios ${entityName ? `en "${entityName}"` : `en este ${entityType}`}?`,
        operation: 'update',
        entityType,
        entityName
      },
      onConfirm
    );
  };

  const confirmDelete = (
    entityType: string,
    entityName: string | undefined,
    onConfirm: () => void | Promise<void>
  ) => {
    openConfirmation(
      {
        title: `Eliminar ${entityType}`,
        message: `¿Estás seguro que deseas eliminar ${entityName ? `"${entityName}"` : `este ${entityType}`}? Esta acción no se puede deshacer.`,
        operation: 'delete',
        entityType,
        entityName
      },
      onConfirm
    );
  };

  return {
    isOpen: state.isOpen,
    isSubmitting: state.isSubmitting,
    options: state.options,

    openConfirmation,
    closeConfirmation,
    handleConfirm,

    confirmCreate,
    confirmUpdate,
    confirmDelete
  };
};