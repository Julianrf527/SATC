import React, { useState } from "react";
import PasswordInput from "@shared/ui/input/PasswordInput";
import type { SetToast } from "../types";
import { useChangePasswordMutation } from "../api/profile";
import { apiErrorMessage } from "../api/errors";

type Props = {
  setToast: SetToast;
  /** Se llama tras cambiar la contraseña: la pantalla cierra la sesión. */
  onSaved: () => void;
};

/** Formulario de cambio de contraseña del perfil. */
export default function PasswordChangeForm({ setToast, onSaved }: Props) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const changePassword = useChangePasswordMutation();
  // Tras un cambio exitoso el formulario sigue bloqueado hasta el logout.
  const [guardado, setGuardado] = useState(false);
  const isSavingPassword = changePassword.isPending || guardado;

  const handleChangePassword = (e: React.FormEvent) => {
    e.preventDefault();

    if (isSavingPassword) return;

    setPasswordError("");

    if (!currentPassword || !newPassword || !confirmPassword) {
      setPasswordError("Todos los campos son obligatorios");
      return;
    }

    if (newPassword.length < 8) {
      setPasswordError("La contraseña debe tener al menos 8 caracteres");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("Las contraseñas no coinciden");
      return;
    }

    changePassword.mutate(
      { current_password: currentPassword, new_password: newPassword },
      {
        onSuccess: () => {
          setGuardado(true);
          setToast({ id: Date.now(), message: "Contraseña actualizada. Cerrando sesión...", type: "success" });
          onSaved();
        },
        onError: (err) =>
          setToast({
            id: Date.now(),
            message: apiErrorMessage(err, "Error al cambiar contraseña", "Error de conexión al cambiar contraseña"),
            type: "error",
          }),
      },
    );
  };

  const handleClearPassword = () => {
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
    setPasswordError("");
  };

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-warning/10 rounded-lg flex items-center justify-center">
          <svg
            className="w-5 h-5 text-warning"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
            />
          </svg>
        </div>
        <div>
          <h3 className="font-semibold text-lg">Seguridad</h3>
          <p className="text-sm text-base-content/60">
            Cambia tu contraseña
          </p>
        </div>
      </div>

      <form
        className="flex flex-col flex-1"
        onSubmit={handleChangePassword}
      >
        <div className="flex-1 space-y-4">
          <PasswordInput
            title="Contraseña actual"
            placeHolder="Ingresa tu contraseña actual"
            value={currentPassword}
            onChange={setCurrentPassword}
          />

          <PasswordInput
            title="Nueva contraseña"
            placeHolder="Mínimo 8 caracteres"
            value={newPassword}
            onChange={setNewPassword}
          />

          <PasswordInput
            title="Confirmar contraseña"
            placeHolder="Confirma tu contraseña"
            value={confirmPassword}
            onChange={setConfirmPassword}
          />

          {passwordError && (
            <div className="alert alert-error py-2">
              <svg
                className="w-4 h-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <span className="text-sm">{passwordError}</span>
            </div>
          )}
        </div>

        {/* Botones - Pegados al final a la misma altura que el otro formulario */}
        <div className="pt-6 space-y-2 mt-auto">
          <button
            type="submit"
            className="btn btn-warning text-white w-full gap-2"
            disabled={isSavingPassword}
          >
            {isSavingPassword ? (
              <>
                <span className="loading loading-spinner loading-sm"></span>
                Actualizando...
              </>
            ) : (
              <>
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
                  />
                </svg>
                Cambiar Contraseña
              </>
            )}
          </button>

          <button
            type="button"
            className="btn btn-ghost w-full gap-2"
            onClick={handleClearPassword}
            disabled={isSavingPassword}
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
            Limpiar
          </button>
        </div>
      </form>
    </div>
  );
}
