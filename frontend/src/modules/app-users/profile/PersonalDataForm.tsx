import React, { useState } from "react";
import Input from "@shared/ui/input/Input";
import MailInput from "@shared/ui/input/MailInput";
import type { PerfilUsuario, SetToast } from "../types";
import { useUpdatePerfilMutation } from "../api/profile";
import { apiErrorMessage } from "../api/errors";
import { capitalize } from "../lib/capitalize";

type Props = {
  /** Valores iniciales (y los que restaura el botón "Restaurar"). */
  perfil: PerfilUsuario;
  setToast: SetToast;
  /** Se llama tras guardar con éxito: la pantalla cierra la sesión. */
  onSaved: () => void;
};

/** Formulario de datos personales del perfil. */
export default function PersonalDataForm({ perfil, setToast, onSaved }: Props) {
  const [firstName, setFirstName] = useState(perfil.primer_nombre);
  const [middleName, setMiddleName] = useState(perfil.segundo_nombre);
  const [lastName, setLastName] = useState(perfil.primer_apellido);
  const [secondLastName, setSecondLastName] = useState(perfil.segundo_apellido);
  const [email, setEmail] = useState(perfil.correo);
  const updatePerfil = useUpdatePerfilMutation();
  // Tras un guardado exitoso el formulario sigue bloqueado hasta el logout.
  const [guardado, setGuardado] = useState(false);
  const isSavingData = updatePerfil.isPending || guardado;

  const handleUpdateData = (e: React.FormEvent) => {
    e.preventDefault();

    if (isSavingData) return;

    if (!firstName.trim()) {
      setToast({ id: Date.now(), message: "El primer nombre es obligatorio", type: "error" });
      return;
    }

    if (!lastName.trim()) {
      setToast({ id: Date.now(), message: "El primer apellido es obligatorio", type: "error" });
      return;
    }

    updatePerfil.mutate(
      {
        first_name: capitalize(firstName),
        middle_name: middleName.trim() ? capitalize(middleName) : "",
        lastname: capitalize(lastName),
        second_lastname: secondLastName.trim() ? capitalize(secondLastName) : "",
        correo: email.toLowerCase(),
      },
      {
        onSuccess: () => {
          setGuardado(true);
          setToast({ id: Date.now(), message: "Datos actualizados. Cerrando sesión...", type: "success" });
          onSaved();
        },
        onError: (err) =>
          setToast({
            id: Date.now(),
            message: apiErrorMessage(err, "Error al actualizar datos", "Error de conexión al actualizar datos"),
            type: "error",
          }),
      },
    );
  };

  const handleRestoreData = () => {
    setFirstName(perfil.primer_nombre);
    setMiddleName(perfil.segundo_nombre);
    setLastName(perfil.primer_apellido);
    setSecondLastName(perfil.segundo_apellido);
    setEmail(perfil.correo);
  };

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-info/10 rounded-lg flex items-center justify-center">
          <svg
            className="w-5 h-5 text-info"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
            />
          </svg>
        </div>
        <div>
          <h3 className="font-semibold text-lg">
            Datos Personales
          </h3>
          <p className="text-sm text-base-content/60">
            Actualiza tu información personal
          </p>
        </div>
      </div>

      <form
        className="flex flex-col flex-1"
        onSubmit={handleUpdateData}
      >
        <div className="flex-1 space-y-4">
          {/* Nombres */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              title="Primer nombre *"
              placeholder="Primer nombre"
              type="text"
              required={true}
              maxLength={20}
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
            />
            <Input
              title="Segundo nombre"
              placeholder="Segundo nombre (opcional)"
              type="text"
              required={false}
              maxLength={20}
              value={middleName}
              onChange={(e) => setMiddleName(e.target.value)}
            />
          </div>

          {/* Apellidos */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Input
              title="Primer apellido *"
              placeholder="Primer apellido"
              type="text"
              required={true}
              maxLength={20}
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
            />
            <Input
              title="Segundo apellido"
              placeholder="Segundo apellido (opcional)"
              type="text"
              required={false}
              maxLength={20}
              value={secondLastName}
              onChange={(e) => setSecondLastName(e.target.value)}
            />
          </div>

          {/* Email */}
          <MailInput
            title="Correo electrónico *"
            value={email}
            onChange={setEmail}
          />
        </div>

        {/* Botones - Pegados al final */}
        <div className="pt-6 space-y-2 mt-auto">
          <button
            type="submit"
            className="btn btn-info text-white w-full gap-2"
            disabled={isSavingData}
          >
            {isSavingData ? (
              <>
                <span className="loading loading-spinner loading-sm"></span>
                Guardando...
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
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Guardar Cambios
              </>
            )}
          </button>

          <button
            type="button"
            className="btn btn-ghost w-full gap-2"
            onClick={handleRestoreData}
            disabled={isSavingData}
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
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Restaurar
          </button>
        </div>
      </form>
    </div>
  );
}
