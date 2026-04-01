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

  /**
   * Abre el modal de confirmación
   */
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

  /**
   * Cierra el modal de confirmación
   */
  const closeConfirmation = () => {
    setState(prev => ({
      ...prev,
      isOpen: false,
      isSubmitting: false
    }));
  };

  /**
   * Ejecuta la acción confirmada
   */
  const handleConfirm = async () => {
    if (!state.onConfirm) return;

    try {
      setState(prev => ({ ...prev, isSubmitting: true }));

      // Ejecutar la acción (puede ser síncrona o asíncrona)
      await state.onConfirm();

      // Cerrar modal después de éxito
      closeConfirmation();
    } catch (error) {
      console.error('Error durante la confirmación:', error);
      // Mantener modal abierto en caso de error para que el usuario see el error
      setState(prev => ({ ...prev, isSubmitting: false }));
    }
  };

  /**
   * Atajos para operaciones específicas
   */
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
    // Estado
    isOpen: state.isOpen,
    isSubmitting: state.isSubmitting,
    options: state.options,

    // Métodos genericos
    openConfirmation,
    closeConfirmation,
    handleConfirm,

    // Atajos específicos
    confirmCreate,
    confirmUpdate,
    confirmDelete
  };
};